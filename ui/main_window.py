"""Janela principal do aplicativo.

A interface nunca executa trabalho pesado na thread do Tkinter: toda a
inferência acontece em threads separadas que se comunicam com a interface por
uma fila (``queue.Queue``) consultada periodicamente com ``after``.
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

from config import (
    APP_NAME,
    APP_VERSION,
    FILE_DIALOG_TYPES,
    LOGO_PATH,
    SUPPORTED_EXTENSIONS,
    THEME,
    BatchReport,
    ProcessingOptions,
)
from services.errors import AppError
from services.image_processor import ImageProcessor
from services.pipeline import RemovalPipeline
from ui.components import (
    Card,
    FileList,
    GhostButton,
    OptionToggle,
    PrimaryButton,
    ProgressPanel,
    StatusBar,
    font,
)
from ui.preview import PreviewArea


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

        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._paths: list[Path] = []
        self._current_index: int = 0
        self._original: Image.Image | None = None
        self._result: Image.Image | None = None
        self._busy: bool = False

        self._build_layout()
        self._enable_drag_and_drop()
        self._poll_events()
        self._warm_up_model()

    # ------------------------------------------------------------------ #
    # Construção da interface
    # ------------------------------------------------------------------ #

    def _build_layout(self) -> None:
        """Cria a estrutura de grade e todos os blocos visuais."""
        self.grid_columnconfigure(0, minsize=330)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_main_area()

    def _build_header(self) -> None:
        """Monta o cabeçalho com logo, nome e versão."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew",
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

        ctk.CTkLabel(
            header,
            text="Remoção de fundo local, sem enviar suas imagens para a internet",
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")

        ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
        ).grid(row=0, column=2, rowspan=2, sticky="e")

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
        sidebar = Card(self)
        sidebar.grid(row=1, column=0, sticky="nsew",
                     padx=(THEME.padding, THEME.gap), pady=(0, 8))
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(3, weight=1)

        pad = 18

        # -- Passo 1: seleção ------------------------------------------- #
        self._section_label(sidebar, "1 · Escolher").grid(
            row=0, column=0, sticky="w", padx=pad, pady=(pad, 8)
        )

        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=pad)
        actions.grid_columnconfigure(0, weight=1)

        self.select_button = PrimaryButton(
            actions, "Selecionar imagens", command=self.select_files
        )
        self.select_button.grid(row=0, column=0, sticky="ew")

        self.clear_button = GhostButton(actions, "Limpar", command=self.clear_all)
        self.clear_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.queue_label = ctk.CTkLabel(
            sidebar,
            text="Nenhuma imagem selecionada",
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        )
        self.queue_label.grid(row=2, column=0, sticky="ew", padx=pad, pady=(14, 6))

        self.file_list = FileList(sidebar, on_select=self.select_from_queue)
        self.file_list.grid(row=3, column=0, sticky="nsew", padx=pad)

        # -- Passo 2: ajustes ------------------------------------------- #
        self._section_label(sidebar, "2 · Ajustes").grid(
            row=4, column=0, sticky="w", padx=pad, pady=(18, 10)
        )

        options_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        options_box.grid(row=5, column=0, sticky="ew", padx=pad)
        options_box.grid_columnconfigure(0, weight=1)

        self.toggles: dict[str, OptionToggle] = {
            "keep_resolution": OptionToggle(
                options_box, "Manter resolução", "Preserva o tamanho original",
                self.options.keep_resolution,
                lambda value: self._set_option("keep_resolution", value),
            ),
            "refine_edges": OptionToggle(
                options_box, "Melhorar bordas", "Remove o halo do recorte",
                self.options.refine_edges,
                lambda value: self._set_option("refine_edges", value),
            ),
            "smooth_contour": OptionToggle(
                options_box, "Suavizar contorno", "Deixa as bordas menos serrilhadas",
                self.options.smooth_contour,
                lambda value: self._set_option("smooth_contour", value),
            ),
            "auto_crop": OptionToggle(
                options_box, "Recorte automático", "Corta as áreas transparentes",
                self.options.auto_crop,
                lambda value: self._set_option("auto_crop", value),
            ),
        }
        for row, toggle in enumerate(self.toggles.values()):
            toggle.grid(row=row, column=0, sticky="ew", pady=6)

        # -- Passo 3: executar ------------------------------------------ #
        self._section_label(sidebar, "3 · Remover e salvar").grid(
            row=6, column=0, sticky="w", padx=pad, pady=(18, 10)
        )

        run_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        run_box.grid(row=7, column=0, sticky="ew", padx=pad, pady=(0, pad))
        run_box.grid_columnconfigure(0, weight=1)

        self.run_button = PrimaryButton(run_box, "Remover fundo", command=self.run)
        self.run_button.grid(row=0, column=0, sticky="ew")

        self.save_button = GhostButton(run_box, "Salvar PNG", command=self.save_result)
        self.save_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.cancel_button = GhostButton(run_box, "Cancelar", command=self.cancel)
        self.cancel_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.cancel_button.grid_remove()

        self.progress = ProgressPanel(run_box)
        self.progress.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        self._set_buttons_state()

    def _build_main_area(self) -> None:
        """Monta a área de pré-visualização e a barra de status."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=1, sticky="nsew", padx=(0, THEME.padding), pady=(0, 8))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.preview = PreviewArea(container)
        self.preview.grid(row=0, column=0, sticky="nsew")

        self.status = StatusBar(container)
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

    def select_files(self) -> None:
        """Abre o seletor de arquivos do sistema."""
        selected = filedialog.askopenfilenames(
            title="Selecione uma ou mais imagens",
            filetypes=FILE_DIALOG_TYPES,
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
                "Nenhuma imagem válida",
                f"Não encontrei imagens suportadas nos itens selecionados.\n\n"
                f"Formatos aceitos: {supported}.",
            )
            return

        self._paths = collected
        self._current_index = 0
        self._result = None
        self.preview.clear_result()
        self.file_list.set_items([item.name for item in collected], selected=0)
        self._update_queue_label()
        self._show_original(0)
        self._set_buttons_state()

        if ignored:
            self.status.show(f"{ignored} arquivo(s) ignorado(s) por formato não suportado.",
                             "warning")

    def select_from_queue(self, index: int) -> None:
        """Exibe a imagem escolhida na fila.

        Args:
            index: Índice do item selecionado.
        """
        if self._busy or not (0 <= index < len(self._paths)):
            return
        self._current_index = index
        self._result = None
        self.preview.clear_result()
        self._show_original(index)
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
        self.status.show(f"{path.name} carregada.", "info")

    def clear_all(self) -> None:
        """Esvazia a fila e volta a interface ao estado inicial."""
        if self._busy:
            return
        self._paths = []
        self._current_index = 0
        self._original = None
        self._result = None
        self.file_list.set_items([])
        self.preview.clear()
        self._update_queue_label()
        self.progress.stop()
        self.status.show("Pronto", "info")
        self._set_buttons_state()

    def _update_queue_label(self) -> None:
        """Atualiza o texto que resume a fila de arquivos."""
        total = len(self._paths)
        if total == 0:
            text = "Nenhuma imagem selecionada"
        elif total == 1:
            text = "1 imagem na fila"
        else:
            text = f"{total} imagens na fila"
        self.queue_label.configure(text=text)

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
        if self._result is not None and not self._busy:
            self.status.show(
                "Ajuste alterado — clique em “Remover fundo” para aplicar.", "warning"
            )

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
        self.progress.start_indeterminate(f"Removendo o fundo de {path.name}…")
        self.status.show("Processando com IA…", "info")

        def worker() -> None:
            """Executa o pipeline fora da thread da interface."""
            try:
                image = self.pipeline.process_image(path, self.options)
                self._events.put(("single_done", image))
            except AppError as exc:
                self._events.put(("error", exc))
            except Exception as exc:  # noqa: BLE001 - rede de segurança
                self._events.put(("error", AppError(
                    "Ocorreu um erro inesperado durante o processamento.",
                    detail=f"{type(exc).__name__}: {exc}",
                )))

        threading.Thread(target=worker, daemon=True).start()

    def _run_batch(self) -> None:
        """Pergunta a pasta de destino e processa toda a fila."""
        destination = filedialog.askdirectory(
            title="Escolha a pasta onde salvar as imagens processadas"
        )
        if not destination:
            return

        destination_dir = Path(destination)
        paths = list(self._paths)

        self._set_busy(True)
        self.progress.set_progress(0, len(paths), "Preparando o lote…")
        self.status.show(f"Processando {len(paths)} imagens…", "info")

        def on_progress(current: int, total: int, name: str) -> None:
            """Repassa o progresso para a interface via fila."""
            self._events.put(("progress", (current, total, name)))

        def worker() -> None:
            """Executa o lote fora da thread da interface."""
            try:
                report = self.pipeline.process_batch(
                    paths, destination_dir, self.options, on_progress
                )
                self._events.put(("batch_done", (report, destination_dir)))
            except Exception as exc:  # noqa: BLE001 - rede de segurança
                self._events.put(("error", AppError(
                    "Ocorreu um erro inesperado durante o lote.",
                    detail=f"{type(exc).__name__}: {exc}",
                )))

        threading.Thread(target=worker, daemon=True).start()

    def cancel(self) -> None:
        """Solicita o cancelamento do lote em andamento."""
        self.pipeline.request_cancel()
        self.status.show("Cancelando após a imagem atual…", "warning")

    # ------------------------------------------------------------------ #
    # Salvamento
    # ------------------------------------------------------------------ #

    def save_result(self) -> None:
        """Salva o recorte atual como PNG transparente."""
        if self._result is None or not self._paths:
            return

        source = self._paths[self._current_index]
        suggested = f"{source.stem}{self.pipeline.exporter.suffix}.png"

        destination = filedialog.asksaveasfilename(
            title="Salvar PNG transparente",
            defaultextension=".png",
            initialfile=suggested,
            initialdir=str(source.parent),
            filetypes=[("PNG", "*.png")],
        )
        if not destination:
            return

        try:
            saved = self.pipeline.exporter.save_png(self._result, Path(destination))
        except AppError as exc:
            self._show_error(exc)
            return

        self.status.show(f"Salvo em {saved}", "success")

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
            self.progress.set_progress(current, total, f"Imagem {current} de {total} · {filename}")
        elif name == "single_done":
            self._on_single_done(payload)
        elif name == "batch_done":
            self._on_batch_done(*payload)
        elif name == "model_ready":
            self.status.show(f"Modelo de IA pronto ({payload}).", "success")
        elif name == "model_failed":
            self.status.show("Modelo de IA será carregado no primeiro uso.", "warning")
        elif name == "error":
            self._set_busy(False)
            self.progress.stop()
            self._show_error(payload)

    def _on_single_done(self, image: Image.Image) -> None:
        """Exibe o resultado de uma imagem única.

        Args:
            image: Imagem processada.
        """
        self._result = image
        self._set_busy(False)
        self.progress.stop()
        self.preview.show_result(image)
        self.status.show("Fundo removido. Clique em “Salvar PNG”.", "success")
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
                f"{report.succeeded} imagem(ns) salva(s) em {destination}", "success"
            )
            messagebox.showinfo(
                "Lote concluído",
                f"{report.succeeded} imagem(ns) processada(s) com sucesso.\n\n"
                f"Pasta: {destination}",
            )
        else:
            preview = "\n".join(
                f"• {item.source.name}: {item.message}" for item in report.failures[:8]
            )
            extra = "" if report.failed <= 8 else f"\n… e mais {report.failed - 8}."
            self.status.show(
                f"{report.succeeded} concluída(s), {report.failed} com erro.", "warning"
            )
            messagebox.showwarning(
                "Lote concluído com avisos",
                f"{report.succeeded} de {report.total} imagens foram salvas em:\n"
                f"{destination}\n\nNão foi possível processar:\n{preview}{extra}",
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

    def _set_buttons_state(self) -> None:
        """Sincroniza o estado dos botões com o contexto atual."""
        has_files = bool(self._paths)
        idle = not self._busy

        self.select_button.configure(state="normal" if idle else "disabled")
        self.clear_button.configure(state="normal" if idle and has_files else "disabled")
        self.save_button.configure(
            state="normal" if idle and self._result is not None else "disabled"
        )

        if self._busy:
            self.run_button.configure(state="disabled", text="Processando…")
        elif len(self._paths) > 1:
            self.run_button.configure(
                state="normal", text=f"Remover fundo de {len(self._paths)} imagens"
            )
        else:
            self.run_button.configure(
                state="normal" if has_files else "disabled", text="Remover fundo"
            )

    def _show_error(self, error: AppError | Exception) -> None:
        """Exibe um erro de forma amigável, sem derrubar o aplicativo.

        Args:
            error: Exceção capturada.
        """
        if isinstance(error, AppError):
            title, message = error.title, error.message
        else:
            title = "Ops, algo deu errado"
            message = f"Ocorreu um erro inesperado.\n\n{type(error).__name__}: {error}"

        self.status.show(message.splitlines()[0], "error")
        messagebox.showerror(title, message)
