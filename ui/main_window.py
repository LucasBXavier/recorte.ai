"""Janela principal do aplicativo.

A interface nunca executa trabalho pesado na thread do Tkinter: toda a
inferência acontece em threads separadas que se comunicam com a interface por
uma fila (``queue.Queue``) consultada periodicamente com ``after``.

O layout é responsivo: a barra lateral tem largura ajustável (arrastando a
faixa entre ela e a pré-visualização) e a área de pré-visualização ocupa todo
o espaço restante da janela.

O recorte bruto da IA (antes de suavização, fundo e redimensionamento) é
mantido em cache por imagem, então ajustar qualquer opção de pós-processamento
atualiza a pré-visualização instantaneamente, sem rodar o modelo de novo.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

from config import (
    APP_NAME,
    APP_VERSION,
    BACKGROUND_MODE_KEYS,
    DEVELOPER_NAME,
    DEVELOPER_URL,
    EXPORT_FORMATS,
    ICON_PATH,
    LOGO_PATH,
    MAIN_AREA_MIN_WIDTH,
    SIDEBAR_MAX_WIDTH,
    SIDEBAR_MIN_WIDTH,
    SPLITTER_WIDTH,
    SUPPORTED_EXTENSIONS,
    THEME,
    BatchReport,
    ProcessingOptions,
)
from i18n import LANGUAGE_LABELS, get_language, set_language, t
from preferences import load_preferences, save_preferences
from services.clipboard import ClipboardError, copy_image
from services.errors import AppError
from services.image_processor import ImageProcessor
from services.pipeline import RawCutout, RemovalPipeline
from ui.components import (
    Card,
    FileList,
    GhostButton,
    LabeledSlider,
    LinkLabel,
    OptionToggle,
    PrimaryButton,
    ProgressPanel,
    SegmentedSelector,
    StatusBar,
    font,
)
from ui.preview import PreviewArea

#: Chave de tradução do verbo de ação exibido, de acordo com o modo de fundo.
_ACTION_KEYS: dict[str, str] = {
    "transparent": "bg.action.transparent",
    "color": "bg.action.change",
    "image": "bg.action.change",
    "blur": "bg.action.blur",
}

#: Chaves de título/descrição de cada opção de pós-processamento (a ordem
#: aqui é a ordem de exibição: "smooth_contour" fica por último para ficar
#: logo acima do seu slider de intensidade).
_TOGGLE_KEYS: dict[str, tuple[str, str]] = {
    "keep_resolution": ("toggle.keep_resolution.title", "toggle.keep_resolution.desc"),
    "refine_edges": ("toggle.refine_edges.title", "toggle.refine_edges.desc"),
    "auto_crop": ("toggle.auto_crop.title", "toggle.auto_crop.desc"),
    "smooth_contour": ("toggle.smooth_contour.title", "toggle.smooth_contour.desc"),
}


class MainWindow(ctk.CTkFrame):
    """Monta e coordena toda a interface do aplicativo."""

    def __init__(self, master: Any, pipeline: RemovalPipeline | None = None) -> None:
        """Inicializa a janela principal.

        Args:
            master: Janela raiz (``CTk`` ou compatível).
            pipeline: Pipeline de processamento. Um novo é criado se omitido.
        """
        super().__init__(master, fg_color=THEME.background)

        self.pipeline = pipeline or RemovalPipeline()
        self.options = ProcessingOptions()

        preferences = load_preferences()
        set_language(preferences.language)
        self._sidebar_width = preferences.sidebar_width

        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._paths: list[Path] = []
        self._current_index: int = 0
        self._original: Image.Image | None = None
        self._result: Image.Image | None = None
        self._results: dict[int, Image.Image] = {}
        self._raw_cutouts: dict[int, RawCutout] = {}
        self._busy: bool = False
        self._background_color_chosen: bool = False
        self._background_image_chosen: bool = False
        self._settings_window: ctk.CTkToplevel | None = None
        self._help_window: ctk.CTkToplevel | None = None
        self._drag_start_x: int = 0
        self._drag_start_width: int = 0

        self._build_layout()
        self._enable_drag_and_drop()
        self._setup_shortcuts()
        self._poll_events()
        self._warm_up_model()

    # ------------------------------------------------------------------ #
    # Construção da interface
    # ------------------------------------------------------------------ #

    def _build_layout(self) -> None:
        """Cria a estrutura de grade e todos os blocos visuais."""
        self.grid_columnconfigure(0, minsize=self._sidebar_width)
        self.grid_columnconfigure(1, minsize=SPLITTER_WIDTH)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_splitter()
        self._build_main_area()

    def _build_header(self) -> None:
        """Monta o cabeçalho com logo, nome, ações rápidas e versão."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew",
                    padx=THEME.padding, pady=(THEME.padding, 10))
        header.grid_columnconfigure(1, weight=1)

        logo_image = self._load_logo()
        if logo_image is not None:
            ctk.CTkLabel(header, text="", image=logo_image).grid(row=0, column=0,
                                                                 rowspan=2, padx=(0, 12))

        ctk.CTkLabel(
            header,
            text=APP_NAME,
            font=font(THEME.size_title, "bold"),
            text_color=THEME.text,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text=t("app.subtitle"),
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        )
        self.subtitle_label.grid(row=1, column=1, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, sticky="e")

        self.help_button = GhostButton(
            actions, t("header.help_button"), command=self._open_help_dialog, height=32
        )
        self.help_button.grid(row=0, column=0, padx=(0, 8))

        self.settings_button = GhostButton(
            actions, t("header.settings_button"), command=self._open_settings_dialog, height=32
        )
        self.settings_button.grid(row=0, column=1)

    def _load_logo(self) -> ctk.CTkImage | None:
        """Carrega o logotipo do disco, se existir.

        Returns:
            Imagem pronta para o CustomTkinter, ou ``None`` se indisponível.
        """
        try:
            if not Path(LOGO_PATH).exists():
                return None
            logo = Image.open(LOGO_PATH).convert("RGBA")
            return ctk.CTkImage(light_image=logo, dark_image=logo, size=(38, 38))
        except Exception:  # noqa: BLE001 - logo é opcional
            return None

    def _build_sidebar(self) -> None:
        """Monta a coluna lateral com ações, fila de arquivos e opções."""
        self.sidebar = Card(self)
        sidebar = self.sidebar
        sidebar.grid(row=1, column=0, sticky="nsew",
                     padx=(THEME.padding, 0), pady=(0, 8))
        sidebar.grid_columnconfigure(0, weight=1)
        # A fila de arquivos e os ajustes dividem o espaço flexível: os
        # ajustes cresceram bastante (fundo, exportação, sliders) e por isso
        # ganham a maior parte, e rolam internamente se ainda não couberem,
        # enquanto a fila e os botões de ação (passo 3) ficam sempre visíveis.
        # A fila só reserva espaço quando há arquivos (ver
        # ``_update_file_list_visibility``): vazia, ela fica escondida em
        # vez de deixar uma caixa grande e em branco.
        sidebar.grid_rowconfigure(5, weight=2, minsize=160)

        pad = 18

        # -- Passo 1: seleção ------------------------------------------- #
        self.step1_label = self._section_label(sidebar, t("step1.title"))
        self.step1_label.grid(row=0, column=0, sticky="w", padx=pad, pady=(pad, 8))

        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=pad)
        actions.grid_columnconfigure(0, weight=1)

        self.select_button = PrimaryButton(
            actions, t("button.select"), command=self.select_files
        )
        self.select_button.grid(row=0, column=0, sticky="ew")

        self.clear_button = GhostButton(actions, t("button.clear"), command=self.clear_all)
        self.clear_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.queue_label = ctk.CTkLabel(
            sidebar,
            text=t("queue.empty"),
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        )
        self.queue_label.grid(row=2, column=0, sticky="ew", padx=pad, pady=(14, 6))

        self.file_list = FileList(sidebar, on_select=self.select_from_queue)
        self.file_list.grid(row=3, column=0, sticky="nsew", padx=pad)

        # -- Passo 2: ajustes ------------------------------------------- #
        self.step2_label = self._section_label(sidebar, t("step2.title"))
        self.step2_label.grid(row=4, column=0, sticky="w", padx=pad, pady=(18, 10))

        options_box = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=THEME.border,
            scrollbar_button_hover_color=THEME.text_muted,
        )
        options_box.grid(row=5, column=0, sticky="nsew", padx=pad)
        options_box.grid_columnconfigure(0, weight=1)

        row = 0

        self.toggles: dict[str, OptionToggle] = {}
        for name, (title_key, desc_key) in _TOGGLE_KEYS.items():
            toggle = OptionToggle(
                options_box,
                t(title_key),
                t(desc_key),
                getattr(self.options, name),
                lambda value, n=name: self._set_option(n, value),
            )
            toggle.grid(row=row, column=0, sticky="ew", pady=6)
            self.toggles[name] = toggle
            row += 1

            if name == "smooth_contour":
                self.smooth_radius_slider = LabeledSlider(
                    options_box,
                    t("slider.smooth_radius"),
                    0.0,
                    5.0,
                    self.options.smooth_radius,
                    command=self._on_smooth_radius_change,
                )
                self.smooth_radius_slider.grid(row=row, column=0, sticky="ew", pady=(0, 6))
                row += 1

        self._update_smooth_radius_visibility()

        # -- Fundo do resultado ------------------------------------------ #
        self.background_label = ctk.CTkLabel(
            options_box,
            text=t("bg.section_title"),
            font=font(THEME.size_small),
            text_color=THEME.text,
            anchor="w",
        )
        self.background_label.grid(row=row, column=0, sticky="ew", pady=(12, 6))
        row += 1

        self.background_selector = SegmentedSelector(
            options_box,
            modes=BACKGROUND_MODE_KEYS,
            labels={key: t(f"bg.mode.{key}") for key in BACKGROUND_MODE_KEYS},
            command=self._on_background_mode_change,
            initial=self.options.background_mode,
        )
        self.background_selector.grid(row=row, column=0, sticky="ew")
        row += 1

        # Cor, imagem e desfoque compartilham a mesma linha: só um aparece
        # por vez, de acordo com o modo de fundo selecionado.
        self.background_color_button = GhostButton(
            options_box, t("bg.color_button.default"), command=self._choose_background_color
        )
        self.background_image_button = GhostButton(
            options_box, t("bg.image_button.default"), command=self._choose_background_image
        )
        self.background_blur_slider = LabeledSlider(
            options_box,
            t("slider.blur_radius"),
            2.0,
            60.0,
            self.options.background_blur_radius,
            command=self._on_blur_radius_change,
        )
        for widget in (
            self.background_color_button,
            self.background_image_button,
            self.background_blur_slider,
        ):
            widget.grid(row=row, column=0, sticky="ew", pady=(8, 0))
        row += 1
        self._update_background_controls()

        # -- Exportação ---------------------------------------------------- #
        self.export_label = ctk.CTkLabel(
            options_box,
            text=t("export.section_title"),
            font=font(THEME.size_small),
            text_color=THEME.text,
            anchor="w",
        )
        self.export_label.grid(row=row, column=0, sticky="ew", pady=(12, 6))
        row += 1

        self.export_format_selector = SegmentedSelector(
            options_box,
            modes=EXPORT_FORMATS,
            labels={fmt: fmt.upper() for fmt in EXPORT_FORMATS},
            command=self._on_export_format_change,
            initial=self.options.export_format,
        )
        self.export_format_selector.grid(row=row, column=0, sticky="ew")
        row += 1

        self.export_quality_slider = LabeledSlider(
            options_box,
            t("slider.export_quality"),
            40,
            100,
            self.options.export_quality,
            command=self._on_export_quality_change,
            value_format="{:.0f}",
        )
        self.export_quality_slider.grid(row=row, column=0, sticky="ew", pady=(8, 0))
        row += 1
        self._update_export_quality_visibility()

        self.resize_toggle = OptionToggle(
            options_box,
            t("toggle.resize_on_export.title"),
            t("toggle.resize_on_export.desc"),
            self.options.resize_on_export,
            lambda value: self._set_option("resize_on_export", value),
        )
        self.resize_toggle.grid(row=row, column=0, sticky="ew", pady=6)
        row += 1

        self.export_max_size_slider = LabeledSlider(
            options_box,
            t("slider.export_max_size"),
            480,
            4000,
            self.options.export_max_size,
            command=self._on_export_max_size_change,
            value_format="{:.0f}px",
        )
        self.export_max_size_slider.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        self._update_export_max_size_visibility()

        # -- Passo 3: executar ------------------------------------------ #
        self.run_section_label = self._section_label(sidebar, self._run_section_text())
        self.run_section_label.grid(row=6, column=0, sticky="w", padx=pad, pady=(18, 10))

        run_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        run_box.grid(row=7, column=0, sticky="ew", padx=pad, pady=(0, pad))
        run_box.grid_columnconfigure(0, weight=1)

        self.run_button = PrimaryButton(run_box, self._current_action_label(), command=self.run)
        self.run_button.grid(row=0, column=0, sticky="ew")

        self.save_button = GhostButton(run_box, self._current_save_label(), command=self.save_result)
        self.save_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.copy_button = GhostButton(run_box, t("button.copy"), command=self.copy_result)
        self.copy_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.cancel_button = GhostButton(run_box, t("button.cancel"), command=self.cancel)
        self.cancel_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.cancel_button.grid_remove()

        self.progress = ProgressPanel(run_box)
        self.progress.grid(row=4, column=0, sticky="ew", pady=(14, 0))

        self._set_buttons_state()
        self._update_file_list_visibility()

    def _update_file_list_visibility(self) -> None:
        """Mostra a fila de arquivos só quando há algo nela.

        Vazia, a lista fica escondida e sua linha não reserva espaço, em vez
        de deixar uma caixa grande e em branco entre o rótulo "Nenhuma imagem
        selecionada" e os ajustes.
        """
        if self._paths:
            self.file_list.grid()
            self.sidebar.grid_rowconfigure(3, weight=1, minsize=90)
        else:
            self.file_list.grid_remove()
            self.sidebar.grid_rowconfigure(3, weight=0, minsize=0)

    def _build_splitter(self) -> None:
        """Monta a faixa arrastável que redimensiona a barra lateral."""
        self.splitter = ctk.CTkFrame(
            self, width=SPLITTER_WIDTH, fg_color="transparent", cursor="sb_h_double_arrow"
        )
        self.splitter.grid(row=1, column=1, sticky="ns", pady=(0, 8))
        self.splitter.grid_propagate(False)

        self._splitter_grip = ctk.CTkFrame(
            self.splitter, width=2, fg_color=THEME.border, corner_radius=1
        )
        self._splitter_grip.place(relx=0.5, rely=0.5, anchor="center", relheight=0.92)

        for widget in (self.splitter, self._splitter_grip):
            widget.bind("<ButtonPress-1>", self._start_sidebar_drag)
            widget.bind("<B1-Motion>", self._do_sidebar_drag)
            widget.bind("<ButtonRelease-1>", self._end_sidebar_drag)
            widget.bind("<Enter>", lambda _e: self._splitter_grip.configure(fg_color=THEME.primary))
            widget.bind("<Leave>", lambda _e: self._splitter_grip.configure(fg_color=THEME.border))

    def _build_main_area(self) -> None:
        """Monta a área de pré-visualização e a barra de status."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=2, sticky="nsew", padx=(0, THEME.padding), pady=(0, 8))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.preview = PreviewArea(container)
        self.preview.grid(row=0, column=0, sticky="nsew")

        self.status = StatusBar(container, version=f"v{APP_VERSION}")
        self.status.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def _section_label(self, master: Any, text: str) -> ctk.CTkLabel:
        """Cria um rótulo de seção da barra lateral.

        Args:
            master: Widget pai.
            text: Texto da seção.

        Returns:
            O rótulo criado (ainda sem posicionamento).
        """
        return ctk.CTkLabel(
            master,
            text=text.upper(),
            font=font(THEME.size_small, "bold"),
            text_color=THEME.text_muted,
            anchor="w",
        )

    # ------------------------------------------------------------------ #
    # Atalhos de teclado
    # ------------------------------------------------------------------ #

    def _setup_shortcuts(self) -> None:
        """Registra atalhos de teclado globais para as ações mais comuns.

        Usa ``bind_all`` (em vez de vincular só à janela) porque widgets do
        CustomTkinter tomam o foco ao serem clicados, e um ``bind`` comum na
        janela raiz não recebe teclas quando outro widget está com o foco.
        Cada atalho confere se a janela principal (não um diálogo auxiliar)
        está em primeiro plano antes de agir.
        """
        root = self.winfo_toplevel()
        bindings = {
            "<Control-o>": self._shortcut_select_files,
            "<Control-O>": self._shortcut_select_files,
            "<Control-s>": self._shortcut_save,
            "<Control-S>": self._shortcut_save,
            "<Control-c>": self._shortcut_copy,
            "<Control-C>": self._shortcut_copy,
            "<Return>": self._shortcut_run,
            "<KP_Enter>": self._shortcut_run,
            "<Delete>": self._shortcut_clear,
        }
        for sequence, handler in bindings.items():
            root.bind_all(sequence, handler)

    def _shortcuts_active(self) -> bool:
        """Indica se os atalhos devem agir agora.

        Retorna ``False`` enquanto um diálogo auxiliar (Opções, Ajuda) está
        aberto, para não disparar ações da janela principal por engano
        enquanto o usuário mexe em outra janela. Checar a existência das
        janelas diretamente é mais confiável do que inferir pelo foco do
        Tkinter, que nem sempre reflete a janela realmente em primeiro plano.

        Returns:
            ``True`` se nenhum diálogo auxiliar estiver aberto.
        """
        if self._settings_window is not None and self._settings_window.winfo_exists():
            return False
        if self._help_window is not None and self._help_window.winfo_exists():
            return False
        return True

    def _shortcut_select_files(self, _event: Any) -> None:
        """Atalho Ctrl+O: abre o seletor de imagens."""
        if self._shortcuts_active():
            self.select_files()

    def _shortcut_save(self, _event: Any) -> None:
        """Atalho Ctrl+S: salva o recorte atual."""
        if self._shortcuts_active():
            self.save_result()

    def _shortcut_copy(self, _event: Any) -> None:
        """Atalho Ctrl+C: copia o recorte atual para a área de transferência."""
        if self._shortcuts_active():
            self.copy_result()

    def _shortcut_run(self, _event: Any) -> None:
        """Atalho Enter: inicia o processamento."""
        if self._shortcuts_active():
            self.run()

    def _shortcut_clear(self, _event: Any) -> None:
        """Atalho Delete: limpa a fila."""
        if self._shortcuts_active():
            self.clear_all()

    # ------------------------------------------------------------------ #
    # Barra lateral redimensionável
    # ------------------------------------------------------------------ #

    def _start_sidebar_drag(self, event: Any) -> None:
        """Registra a posição inicial do arraste da divisória.

        Args:
            event: Evento de clique do Tkinter.
        """
        self._drag_start_x = event.x_root
        self._drag_start_width = self._sidebar_width

    def _do_sidebar_drag(self, event: Any) -> None:
        """Redimensiona a barra lateral conforme o mouse se move.

        Args:
            event: Evento de movimento do Tkinter.
        """
        delta = event.x_root - self._drag_start_x
        proposed = self._drag_start_width + delta
        max_allowed = max(
            SIDEBAR_MIN_WIDTH, self.winfo_width() - MAIN_AREA_MIN_WIDTH - SPLITTER_WIDTH
        )
        new_width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, max_allowed, proposed))
        self._sidebar_width = new_width
        self.grid_columnconfigure(0, minsize=new_width)

    def _end_sidebar_drag(self, _event: Any) -> None:
        """Persiste a nova largura da barra lateral ao soltar o mouse."""
        preferences = load_preferences()
        preferences.sidebar_width = self._sidebar_width
        save_preferences(preferences)

    # ------------------------------------------------------------------ #
    # Opções, ajuda e idioma
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apply_dialog_icon(dialog: ctk.CTkToplevel) -> None:
        """Aplica o ícone do aplicativo a uma janela auxiliar, se possível.

        Args:
            dialog: Janela auxiliar (``CTkToplevel``).
        """
        try:
            if Path(ICON_PATH).exists():
                dialog.iconbitmap(str(ICON_PATH))
        except Exception:  # noqa: BLE001 - ícone é opcional
            pass

    def _open_settings_dialog(self) -> None:
        """Abre (ou traz para frente) a janela de opções, com o seletor de idioma."""
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("settings.title"))
        dialog.geometry("340x210")
        dialog.resizable(False, False)
        dialog.configure(fg_color=THEME.background)
        dialog.transient(self.winfo_toplevel())
        self._apply_dialog_icon(dialog)
        self._settings_window = dialog

        ctk.CTkLabel(
            dialog,
            text=t("settings.language_label"),
            font=font(THEME.size_body, "bold"),
            text_color=THEME.text,
            anchor="w",
        ).pack(padx=24, pady=(24, 8), anchor="w")

        current_label = LANGUAGE_LABELS.get(get_language(), next(iter(LANGUAGE_LABELS.values())))
        menu = ctk.CTkOptionMenu(
            dialog,
            values=list(LANGUAGE_LABELS.values()),
            fg_color=THEME.surface,
            button_color=THEME.primary,
            button_hover_color=THEME.primary_hover,
            dropdown_fg_color=THEME.surface,
            command=self._on_language_selected,
        )
        menu.set(current_label)
        menu.pack(padx=24, pady=(0, 20), fill="x")

        GhostButton(dialog, t("settings.close"), command=dialog.destroy).pack(
            padx=24, pady=(0, 24), fill="x"
        )

    def _on_language_selected(self, label: str) -> None:
        """Troca o idioma da interface a partir do seletor de opções.

        Args:
            label: Nome do idioma escolhido (ex.: ``"English"``).
        """
        code = next((c for c, name in LANGUAGE_LABELS.items() if name == label), None)
        if code is None or code == get_language():
            return

        set_language(code)
        preferences = load_preferences()
        preferences.language = code
        save_preferences(preferences)
        self._apply_language()

    def _open_help_dialog(self) -> None:
        """Abre (ou traz para frente) a janela de ajuda rápida."""
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.lift()
            self._help_window.focus_force()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("help.title"))
        dialog.geometry("460x450")
        dialog.resizable(False, False)
        dialog.configure(fg_color=THEME.background)
        dialog.transient(self.winfo_toplevel())
        self._apply_dialog_icon(dialog)
        self._help_window = dialog

        ctk.CTkLabel(
            dialog,
            text=f"{APP_NAME} · v{APP_VERSION}",
            font=font(THEME.size_body, "bold"),
            text_color=THEME.text,
            anchor="w",
        ).pack(padx=24, pady=(24, 12), anchor="w")

        ctk.CTkLabel(
            dialog,
            text=t("help.body"),
            font=font(THEME.size_small),
            text_color=THEME.text_secondary,
            justify="left",
            anchor="w",
            wraplength=410,
        ).pack(padx=24, pady=(0, 16), anchor="w")

        credit_row = ctk.CTkFrame(dialog, fg_color="transparent")
        credit_row.pack(padx=24, pady=(0, 16), anchor="w")

        ctk.CTkLabel(
            credit_row,
            text=t("help.credit_prefix"),
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
        ).pack(side="left")

        LinkLabel(credit_row, DEVELOPER_NAME, DEVELOPER_URL).pack(side="left", padx=(4, 0))

        GhostButton(dialog, t("settings.close"), command=dialog.destroy).pack(
            padx=24, pady=(0, 24), fill="x"
        )

    def _apply_language(self) -> None:
        """Retextualiza todos os elementos fixos da interface no idioma atual."""
        self.subtitle_label.configure(text=t("app.subtitle"))
        self.help_button.configure(text=t("header.help_button"))
        self.settings_button.configure(text=t("header.settings_button"))

        self.step1_label.configure(text=t("step1.title").upper())
        self.select_button.configure(text=t("button.select"))
        self.clear_button.configure(text=t("button.clear"))
        self._update_queue_label()

        self.step2_label.configure(text=t("step2.title").upper())
        for name, toggle in self.toggles.items():
            title_key, desc_key = _TOGGLE_KEYS[name]
            toggle.set_texts(t(title_key), t(desc_key))
        self.smooth_radius_slider.set_label(t("slider.smooth_radius"))

        self.background_label.configure(text=t("bg.section_title"))
        self.background_selector.set_labels(
            {key: t(f"bg.mode.{key}") for key in BACKGROUND_MODE_KEYS}
        )
        self.background_blur_slider.set_label(t("slider.blur_radius"))

        if self._background_color_chosen:
            self.background_color_button.configure(
                text=t("bg.color_button.chosen", hex=self.options.background_color)
            )
        else:
            self.background_color_button.configure(text=t("bg.color_button.default"))

        if self._background_image_chosen and self.options.background_image_path:
            self.background_image_button.configure(
                text=t(
                    "bg.image_button.chosen",
                    name=Path(self.options.background_image_path).name,
                )
            )
        else:
            self.background_image_button.configure(text=t("bg.image_button.default"))

        self.export_label.configure(text=t("export.section_title"))
        self.export_quality_slider.set_label(t("slider.export_quality"))
        self.resize_toggle.set_texts(
            t("toggle.resize_on_export.title"), t("toggle.resize_on_export.desc")
        )
        self.export_max_size_slider.set_label(t("slider.export_max_size"))

        self.run_section_label.configure(text=self._run_section_text())
        self.save_button.configure(text=self._current_save_label())
        self.copy_button.configure(text=t("button.copy"))
        self.cancel_button.configure(text=t("button.cancel"))
        self._set_buttons_state()

        self.preview.apply_language()

        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.destroy()
            self._settings_window = None
            self._open_settings_dialog()
        if self._help_window is not None and self._help_window.winfo_exists():
            self._help_window.destroy()
            self._help_window = None
            self._open_help_dialog()

    # ------------------------------------------------------------------ #
    # Drag and drop
    # ------------------------------------------------------------------ #

    def _enable_drag_and_drop(self) -> None:
        """Registra a janela como alvo de arrastar e soltar, se disponível."""
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            return

        root = self.winfo_toplevel()
        if not hasattr(root, "drop_target_register"):
            return

        try:
            root.drop_target_register(DND_FILES)
            root.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:  # noqa: BLE001 - recurso opcional
            return

    def _on_drop(self, event: Any) -> None:
        """Trata arquivos soltos sobre a janela.

        Args:
            event: Evento do ``tkinterdnd2`` com o atributo ``data``.
        """
        if self._busy:
            return
        try:
            raw = self.tk.splitlist(event.data)
        except Exception:  # noqa: BLE001 - formato inesperado do gerenciador
            raw = [event.data]
        self.load_paths([Path(str(item)) for item in raw])

    # ------------------------------------------------------------------ #
    # Seleção de arquivos
    # ------------------------------------------------------------------ #

    def _file_dialog_types(self) -> list[tuple[str, str]]:
        """Monta os filtros de formato para os seletores de arquivo do sistema.

        Returns:
            Lista de pares ``(rótulo, padrão)`` no idioma atual.
        """
        return [
            (t("filedialog.images_label"), "*.png *.jpg *.jpeg *.webp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("WEBP", "*.webp"),
            (t("filedialog.all_files_label"), "*.*"),
        ]

    def select_files(self) -> None:
        """Abre o seletor de arquivos do sistema."""
        if self._busy:
            return
        selected = filedialog.askopenfilenames(
            title=t("filedialog.select_images"),
            filetypes=self._file_dialog_types(),
        )
        if selected:
            self.load_paths([Path(item) for item in selected])

    def load_paths(self, paths: list[Path]) -> None:
        """Valida e carrega uma lista de caminhos na fila.

        Pastas são expandidas para as imagens que contêm. Arquivos com extensão
        não suportada são ignorados com um aviso.

        Args:
            paths: Caminhos vindos do seletor ou do arrastar e soltar.
        """
        collected: list[Path] = []
        ignored = 0

        for path in paths:
            if path.is_dir():
                collected.extend(
                    sorted(
                        item for item in path.iterdir()
                        if item.is_file() and ImageProcessor.is_supported(item)
                    )
                )
            elif ImageProcessor.is_supported(path):
                collected.append(path)
            else:
                ignored += 1

        if not collected:
            supported = ", ".join(ext.upper().lstrip(".") for ext in SUPPORTED_EXTENSIONS)
            messagebox.showwarning(
                t("dialog.no_valid_images.title"),
                t("dialog.no_valid_images.body", formats=supported),
            )
            return

        self._paths = collected
        self._current_index = 0
        self._result = None
        self._results = {}
        self._raw_cutouts = {}
        self.preview.clear_result()
        self.file_list.set_items([item.name for item in collected], selected=0)
        self._update_queue_label()
        self._show_original(0)
        self._set_buttons_state()

        if ignored:
            self.status.show(t("status.ignored_files", n=ignored), "warning")

    def select_from_queue(self, index: int) -> None:
        """Exibe a imagem escolhida na fila.

        Args:
            index: Índice do item selecionado.
        """
        if self._busy or not (0 <= index < len(self._paths)):
            return
        self._current_index = index
        self._show_original(index)

        cached = self._results.get(index)
        self._result = cached
        if cached is not None:
            self.preview.show_result(cached)
        else:
            self.preview.clear_result()
        self._set_buttons_state()

    def _show_original(self, index: int) -> None:
        """Carrega e exibe a imagem original de um índice da fila.

        Args:
            index: Posição na fila.
        """
        path = self._paths[index]
        try:
            self._original = ImageProcessor.load(path)
        except AppError as exc:
            self._original = None
            self.preview.clear()
            self._show_error(exc)
            return

        self.preview.show_original(self._original)
        self.status.show(t("status.loaded", name=path.name), "info")

    def clear_all(self) -> None:
        """Esvazia a fila e volta a interface ao estado inicial."""
        if self._busy:
            return
        self._paths = []
        self._current_index = 0
        self._original = None
        self._result = None
        self._results = {}
        self._raw_cutouts = {}
        self.file_list.set_items([])
        self.preview.clear()
        self._update_queue_label()
        self.progress.stop()
        self.status.show(t("status.ready"), "info")
        self._set_buttons_state()

    def _update_queue_label(self) -> None:
        """Atualiza o texto que resume a fila de arquivos."""
        total = len(self._paths)
        if total == 0:
            text = t("queue.empty")
        elif total == 1:
            text = t("queue.one")
        else:
            text = t("queue.many", n=total)
        self.queue_label.configure(text=text)
        self._update_file_list_visibility()

    # ------------------------------------------------------------------ #
    # Pré-visualização ao vivo
    # ------------------------------------------------------------------ #

    def _refresh_current_preview(self) -> bool:
        """Reaplica as opções de pós-processamento ao recorte já calculado.

        Usa o recorte bruto em cache (resultado da IA) para a imagem atual,
        sem rodar o modelo de novo: é isso que torna sliders e toggles
        instantâneos depois do primeiro processamento.

        Returns:
            ``True`` se havia um recorte em cache e a pré-visualização foi
            atualizada; ``False`` se nada pôde ser recalculado ainda (nenhum
            processamento rodou para esta imagem, ou o app está ocupado).
        """
        if self._busy:
            return False
        cached = self._raw_cutouts.get(self._current_index)
        if cached is None:
            return False

        cutout, original_size, source = cached
        try:
            processed = ImageProcessor.apply_options(cutout, self.options, original_size, source)
        except Exception:  # noqa: BLE001 - pré-visualização é best-effort
            return False

        self._result = processed
        self._results[self._current_index] = processed
        self.preview.show_result(processed)
        self._set_buttons_state()
        return True

    def _notify_option_changed(self) -> None:
        """Atualiza a pré-visualização ao vivo, ou avisa para reprocessar.

        Chamado por qualquer opção que precise de um novo recorte da IA para
        ter efeito visível. Se já existe um recorte em cache, o resultado é
        atualizado na hora; caso contrário (nada processado ainda), mostra o
        aviso tradicional pedindo para clicar no botão de ação.
        """
        if not self._refresh_current_preview() and self._result is not None and not self._busy:
            self.status.show(
                t("status.adjust_changed", action=self._current_action_label()), "warning"
            )

    # ------------------------------------------------------------------ #
    # Opções
    # ------------------------------------------------------------------ #

    def _set_option(self, name: str, value: bool) -> None:
        """Atualiza uma opção de processamento.

        Args:
            name: Nome do atributo em :class:`ProcessingOptions`.
            value: Novo valor.
        """
        setattr(self.options, name, value)
        if name == "smooth_contour":
            self._update_smooth_radius_visibility()
        elif name == "resize_on_export":
            self._update_export_max_size_visibility()
        self._notify_option_changed()

    def _current_action_label(self) -> str:
        """Verbo de ação correspondente ao modo de fundo selecionado.

        Returns:
            Texto traduzido, ex.: "Remover fundo", "Trocar fundo" ou
            "Desfocar fundo" (ou seus equivalentes em outro idioma).
        """
        key = _ACTION_KEYS.get(self.options.background_mode, "bg.action.transparent")
        return t(key)

    def _current_save_label(self) -> str:
        """Texto do botão de salvar, de acordo com o formato de exportação.

        Returns:
            "Salvar PNG"/"Salvar WEBP" (ou equivalente no idioma ativo).
        """
        key = "button.save_webp" if self.options.export_format == "webp" else "button.save_png"
        return t(key)

    def _run_section_text(self) -> str:
        """Monta o texto do título da seção 3, já traduzido e em maiúsculas."""
        return f"3 · {self._current_action_label()} {t('step3.and_save')}".upper()

    def _on_background_mode_change(self, mode: str) -> None:
        """Reage à troca do modo de fundo escolhido na barra lateral.

        Args:
            mode: Chave do novo modo (``"transparent"``, ``"color"``,
                ``"image"`` ou ``"blur"``).
        """
        self.options.background_mode = mode
        self._update_background_controls()
        self.run_section_label.configure(text=self._run_section_text())
        self._set_buttons_state()
        self._notify_option_changed()

    def _update_background_controls(self) -> None:
        """Mostra apenas o controle relevante para o modo de fundo ativo."""
        mode = self.options.background_mode
        self.background_color_button.grid_remove()
        self.background_image_button.grid_remove()
        self.background_blur_slider.grid_remove()
        if mode == "color":
            self.background_color_button.grid()
        elif mode == "image":
            self.background_image_button.grid()
        elif mode == "blur":
            self.background_blur_slider.grid()

    def _update_smooth_radius_visibility(self) -> None:
        """Mostra o slider de suavização só quando a opção está ativa."""
        if self.options.smooth_contour:
            self.smooth_radius_slider.grid()
        else:
            self.smooth_radius_slider.grid_remove()

    def _update_export_quality_visibility(self) -> None:
        """Mostra o slider de qualidade só para o formato WEBP."""
        if self.options.export_format == "webp":
            self.export_quality_slider.grid()
        else:
            self.export_quality_slider.grid_remove()

    def _update_export_max_size_visibility(self) -> None:
        """Mostra o slider de redimensionamento só quando a opção está ativa."""
        if self.options.resize_on_export:
            self.export_max_size_slider.grid()
        else:
            self.export_max_size_slider.grid_remove()

    def _on_smooth_radius_change(self, value: float) -> None:
        """Atualiza a intensidade da suavização ao vivo.

        Args:
            value: Novo raio de suavização.
        """
        self.options.smooth_radius = value
        self._refresh_current_preview()

    def _on_blur_radius_change(self, value: float) -> None:
        """Atualiza a intensidade do desfoque de fundo ao vivo.

        Args:
            value: Novo raio de desfoque.
        """
        self.options.background_blur_radius = value
        self._refresh_current_preview()

    def _on_export_format_change(self, fmt: str) -> None:
        """Reage à troca do formato de exportação.

        Args:
            fmt: Novo formato (``"png"`` ou ``"webp"``).
        """
        self.options.export_format = fmt
        self._update_export_quality_visibility()
        self.save_button.configure(text=self._current_save_label())

    def _on_export_quality_change(self, value: float) -> None:
        """Atualiza a qualidade de compressão do WEBP.

        Args:
            value: Nova qualidade (1-100).
        """
        self.options.export_quality = int(value)

    def _on_export_max_size_change(self, value: float) -> None:
        """Atualiza o limite de redimensionamento ao exportar, ao vivo.

        Args:
            value: Novo maior lado permitido, em pixels.
        """
        self.options.export_max_size = int(value)
        self._refresh_current_preview()

    def _choose_background_color(self) -> None:
        """Abre o seletor de cor do sistema para o fundo sólido."""
        _, hex_color = colorchooser.askcolor(
            color=self.options.background_color, title=t("filedialog.choose_color")
        )
        if not hex_color:
            return
        self.options.background_color = hex_color
        self._background_color_chosen = True
        self.background_color_button.configure(
            text=t("bg.color_button.chosen", hex=hex_color),
            fg_color=hex_color,
            text_color=self._contrast_color(hex_color),
        )
        self._notify_option_changed()

    def _choose_background_image(self) -> None:
        """Abre o seletor de arquivo para a imagem de fundo personalizada."""
        selected = filedialog.askopenfilename(
            title=t("filedialog.choose_image"),
            filetypes=self._file_dialog_types(),
        )
        if not selected:
            return
        self.options.background_image_path = selected
        self._background_image_chosen = True
        self.background_image_button.configure(
            text=t("bg.image_button.chosen", name=Path(selected).name)
        )
        self._notify_option_changed()

    @staticmethod
    def _contrast_color(hex_color: str) -> str:
        """Escolhe preto ou branco conforme o contraste com a cor de fundo.

        Args:
            hex_color: Cor no formato ``"#RRGGBB"``.

        Returns:
            ``"#111111"`` para cores claras ou ``"#FFFFFF"`` para escuras.
        """
        value = hex_color.lstrip("#")
        r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#111111" if luminance > 150 else "#FFFFFF"

    # ------------------------------------------------------------------ #
    # Execução
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Inicia o processamento da imagem atual ou de todo o lote."""
        if self._busy or not self._paths:
            return
        if len(self._paths) == 1:
            self._run_single()
        else:
            self._run_batch()

    def _run_single(self) -> None:
        """Processa apenas a imagem selecionada, mantendo o resultado na tela."""
        path = self._paths[self._current_index]
        self._set_busy(True)
        self.progress.start_indeterminate(t("status.processing_file", name=path.name))
        self.status.show(t("status.processing_ai"), "info")

        def worker() -> None:
            """Executa o pipeline fora da thread da interface."""
            try:
                cutout, original_size, source = self.pipeline.remove_background_only(path)
                image = ImageProcessor.apply_options(cutout, self.options, original_size, source)
                self._events.put(("single_done", (cutout, original_size, source, image)))
            except AppError as exc:
                self._events.put(("error", exc))
            except Exception as exc:  # noqa: BLE001 - rede de segurança
                self._events.put(("error", AppError(
                    t("error.unexpected_processing"),
                    detail=f"{type(exc).__name__}: {exc}",
                )))

        threading.Thread(target=worker, daemon=True).start()

    def _run_batch(self) -> None:
        """Pergunta a pasta de destino e processa toda a fila."""
        destination = filedialog.askdirectory(title=t("filedialog.choose_destination"))
        if not destination:
            return

        destination_dir = Path(destination)
        paths = list(self._paths)

        self._set_busy(True)
        self.progress.set_progress(0, len(paths), t("status.batch_preparing"))
        self.status.show(t("status.batch_processing", n=len(paths)), "info")

        def on_progress(current: int, total: int, name: str) -> None:
            """Repassa o progresso para a interface via fila."""
            self._events.put(("progress", (current, total, name)))

        def on_item(
            current: int,
            total: int,
            result: Any,
            image: Image.Image | None,
            raw: RawCutout | None,
        ) -> None:
            """Repassa o resultado de cada imagem do lote assim que fica pronto."""
            self._events.put(("batch_item", (current - 1, result, image, raw)))

        def worker() -> None:
            """Executa o lote fora da thread da interface."""
            try:
                report = self.pipeline.process_batch(
                    paths, destination_dir, self.options, on_progress, on_item
                )
                self._events.put(("batch_done", (report, destination_dir)))
            except Exception as exc:  # noqa: BLE001 - rede de segurança
                self._events.put(("error", AppError(
                    t("error.unexpected_batch"),
                    detail=f"{type(exc).__name__}: {exc}",
                )))

        threading.Thread(target=worker, daemon=True).start()

    def cancel(self) -> None:
        """Solicita o cancelamento do lote em andamento."""
        self.pipeline.request_cancel()
        self.status.show(t("status.cancelling"), "warning")

    # ------------------------------------------------------------------ #
    # Salvamento
    # ------------------------------------------------------------------ #

    def save_result(self) -> None:
        """Salva o recorte atual no formato configurado (PNG ou WEBP)."""
        if self._result is None or not self._paths:
            return

        fmt = self.options.export_format
        extension = ".webp" if fmt == "webp" else ".png"
        source = self._paths[self._current_index]
        suggested = f"{source.stem}{self.pipeline.exporter.suffix}{extension}"

        destination = filedialog.asksaveasfilename(
            title=t("filedialog.save_image"),
            defaultextension=extension,
            initialfile=suggested,
            initialdir=str(source.parent),
            filetypes=[("WEBP", "*.webp")] if fmt == "webp" else [("PNG", "*.png")],
        )
        if not destination:
            return

        try:
            saved = self.pipeline.exporter.save_image(
                self._result, Path(destination), format=fmt, quality=self.options.export_quality
            )
        except AppError as exc:
            self._show_error(exc)
            return

        self.status.show(t("status.saved", path=saved), "success")

    def copy_result(self) -> None:
        """Copia o recorte atual para a área de transferência, sem salvar em disco."""
        if self._result is None:
            return

        try:
            copy_image(self._result)
        except ClipboardError as exc:
            self._show_error(exc)
            return

        self.status.show(t("status.copied"), "success")

    # ------------------------------------------------------------------ #
    # Fila de eventos das threads
    # ------------------------------------------------------------------ #

    def _poll_events(self) -> None:
        """Consome a fila de eventos das threads e reagenda a próxima leitura."""
        try:
            while True:
                name, payload = self._events.get_nowait()
                self._handle_event(name, payload)
        except queue.Empty:
            pass
        finally:
            self.after(80, self._poll_events)

    def _handle_event(self, name: str, payload: Any) -> None:
        """Trata um evento vindo de uma thread de trabalho.

        Args:
            name: Identificador do evento.
            payload: Dados associados ao evento.
        """
        if name == "progress":
            current, total, filename = payload
            self.progress.set_progress(
                current, total, t("progress.item", current=current, total=total, name=filename)
            )
        elif name == "single_done":
            self._on_single_done(*payload)
        elif name == "batch_item":
            self._on_batch_item(*payload)
        elif name == "batch_done":
            self._on_batch_done(*payload)
        elif name == "model_ready":
            self.status.show(t("status.model_ready", model=payload), "success")
        elif name == "model_failed":
            self.status.show(t("status.model_pending"), "warning")
        elif name == "error":
            self._set_busy(False)
            self.progress.stop()
            self._show_error(payload)

    def _on_single_done(
        self,
        cutout: Image.Image,
        original_size: tuple[int, int],
        source: Image.Image,
        image: Image.Image,
    ) -> None:
        """Exibe o resultado de uma imagem única e guarda o recorte bruto.

        Args:
            cutout: Recorte bruto devolvido pela IA (antes dos ajustes).
            original_size: Tamanho da imagem original.
            source: Imagem original (antes da remoção de fundo).
            image: Imagem final, já com os ajustes aplicados.
        """
        self._raw_cutouts[self._current_index] = (cutout, original_size, source)
        self._result = image
        self._results[self._current_index] = image
        self._set_busy(False)
        self.progress.stop()
        self.preview.show_result(image)
        self.status.show(t("status.single_done", save=self._current_save_label()), "success")
        self._set_buttons_state()

    def _on_batch_item(
        self,
        index: int,
        result: Any,
        image: Image.Image | None,
        raw: RawCutout | None,
    ) -> None:
        """Exibe o resultado de uma imagem do lote assim que ela é processada.

        Args:
            index: Posição da imagem na fila (base zero).
            result: Resultado individual retornado pelo pipeline.
            image: Imagem processada, ou ``None`` se essa imagem falhou.
            raw: Recorte bruto da IA para essa imagem, ou ``None`` se falhou.
        """
        if image is not None:
            self._results[index] = image
            self.file_list.mark_done(index)
            if raw is not None:
                self._raw_cutouts[index] = raw
        else:
            self.file_list.mark_error(index)

        if index == self._current_index:
            self._result = image
            if image is not None:
                self.preview.show_result(image)
            self._set_buttons_state()

    def _on_batch_done(self, report: BatchReport, destination: Path) -> None:
        """Informa o resultado de um processamento em lote.

        Args:
            report: Relatório com sucessos e falhas.
            destination: Pasta onde os arquivos foram gravados.
        """
        self._set_busy(False)
        self.progress.stop()

        if report.failed == 0:
            self.status.show(
                t("status.batch_success", ok=report.succeeded, dest=destination), "success"
            )
            messagebox.showinfo(
                t("dialog.batch_done.title"),
                t("dialog.batch_done.body", ok=report.succeeded, dest=destination),
            )
        else:
            preview = "\n".join(
                f"• {item.source.name}: {item.message}" for item in report.failures[:8]
            )
            extra = (
                ""
                if report.failed <= 8
                else t("dialog.batch_warning.extra", n=report.failed - 8)
            )
            self.status.show(
                t("status.batch_partial", ok=report.succeeded, fail=report.failed), "warning"
            )
            messagebox.showwarning(
                t("dialog.batch_warning.title"),
                t(
                    "dialog.batch_warning.body",
                    ok=report.succeeded,
                    total=report.total,
                    dest=destination,
                    preview=preview,
                    extra=extra,
                ),
            )

        self._set_buttons_state()

    # ------------------------------------------------------------------ #
    # Modelo de IA
    # ------------------------------------------------------------------ #

    def _warm_up_model(self) -> None:
        """Carrega o modelo em segundo plano para agilizar o primeiro uso."""

        def worker() -> None:
            """Inicializa a sessão do modelo fora da thread da interface."""
            try:
                model = self.pipeline.remover.warm_up()
                self._events.put(("model_ready", model))
            except AppError:
                self._events.put(("model_failed", None))
            except Exception:  # noqa: BLE001 - aquecimento é best-effort
                self._events.put(("model_failed", None))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Estado da interface
    # ------------------------------------------------------------------ #

    def _set_busy(self, busy: bool) -> None:
        """Bloqueia ou libera os controles durante o processamento.

        Args:
            busy: ``True`` enquanto houver trabalho em andamento.
        """
        self._busy = busy
        self._set_buttons_state()

        if busy and len(self._paths) > 1:
            self.cancel_button.grid()
        else:
            self.cancel_button.grid_remove()

        for toggle in self.toggles.values():
            toggle.set_enabled(not busy)
        self.resize_toggle.set_enabled(not busy)
        self.background_selector.set_enabled(not busy)
        self.background_color_button.configure(state="normal" if not busy else "disabled")
        self.background_image_button.configure(state="normal" if not busy else "disabled")
        self.smooth_radius_slider.set_enabled(not busy)
        self.background_blur_slider.set_enabled(not busy)
        self.export_format_selector.set_enabled(not busy)
        self.export_quality_slider.set_enabled(not busy)
        self.export_max_size_slider.set_enabled(not busy)

    def _set_buttons_state(self) -> None:
        """Sincroniza o estado dos botões com o contexto atual."""
        has_files = bool(self._paths)
        idle = not self._busy
        has_result = self._result is not None

        self.select_button.configure(state="normal" if idle else "disabled")
        self.clear_button.configure(state="normal" if idle and has_files else "disabled")
        self.save_button.configure(state="normal" if idle and has_result else "disabled")
        self.copy_button.configure(state="normal" if idle and has_result else "disabled")

        action = self._current_action_label()
        if self._busy:
            self.run_button.configure(state="disabled", text=t("button.processing"))
        elif len(self._paths) > 1:
            self.run_button.configure(
                state="normal", text=f"{action} · {len(self._paths)}"
            )
        else:
            self.run_button.configure(
                state="normal" if has_files else "disabled", text=action
            )

    def _show_error(self, error: AppError | Exception) -> None:
        """Exibe um erro de forma amigável, sem derrubar o aplicativo.

        Args:
            error: Exceção capturada.
        """
        if isinstance(error, AppError):
            title, message = error.title, error.message
        else:
            title = t("error.generic_title")
            message = t("error.generic_body", type=type(error).__name__, error=error)

        self.status.show(message.splitlines()[0], "error")
        messagebox.showerror(title, message)
