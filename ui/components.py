"""Componentes reutilizáveis da interface.

Todos seguem a paleta definida em :data:`config.THEME`, garantindo consistência
visual e evitando repetição de parâmetros de estilo pela aplicação.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from config import DEVELOPER_NAME, DEVELOPER_URL, THEME


def font(size: int = THEME.size_body, weight: str = "normal") -> ctk.CTkFont:
    """Cria uma fonte padronizada do aplicativo.

    Args:
        size: Tamanho em pontos.
        weight: ``"normal"`` ou ``"bold"``.

    Returns:
        Objeto de fonte pronto para uso em widgets do CustomTkinter.
    """
    return ctk.CTkFont(family=THEME.font_family, size=size, weight=weight)


class LinkLabel(ctk.CTkLabel):
    """Rótulo clicável que abre uma URL no navegador padrão do sistema."""

    def __init__(self, master: Any, text: str, url: str, **kwargs: Any) -> None:
        """Inicializa o link.

        Args:
            master: Widget pai.
            text: Texto exibido.
            url: Endereço aberto ao clicar.
            **kwargs: Parâmetros extras repassados ao ``CTkLabel``.
        """
        kwargs.setdefault("text_color", THEME.primary)
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("font", font(THEME.size_small, "bold"))
        super().__init__(master, text=text, **kwargs)
        self._url = url
        self.bind("<Button-1>", self._open)

    def _open(self, _event: Any) -> None:
        """Abre a URL configurada no navegador padrão."""
        webbrowser.open(self._url)

    def set_url(self, url: str) -> None:
        """Atualiza o endereço aberto ao clicar.

        Args:
            url: Novo endereço.
        """
        self._url = url


class Card(ctk.CTkFrame):
    """Painel com cantos arredondados usado como bloco visual da interface."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        """Inicializa o cartão.

        Args:
            master: Widget pai.
            **kwargs: Parâmetros extras repassados ao ``CTkFrame``.
        """
        kwargs.setdefault("fg_color", THEME.card)
        kwargs.setdefault("corner_radius", THEME.radius_large)
        super().__init__(master, **kwargs)


class PrimaryButton(ctk.CTkButton):
    """Botão de ação principal, em azul."""

    def __init__(self, master: Any, text: str, command: Callable[[], None] | None = None,
                 **kwargs: Any) -> None:
        """Inicializa o botão principal.

        Args:
            master: Widget pai.
            text: Rótulo exibido.
            command: Função chamada ao clicar.
            **kwargs: Parâmetros extras repassados ao ``CTkButton``.
        """
        kwargs.setdefault("fg_color", THEME.primary)
        kwargs.setdefault("hover_color", THEME.primary_hover)
        kwargs.setdefault("text_color", THEME.text)
        kwargs.setdefault("corner_radius", THEME.radius)
        kwargs.setdefault("height", 44)
        kwargs.setdefault("font", font(THEME.size_body, "bold"))
        super().__init__(master, text=text, command=command, **kwargs)


class GhostButton(ctk.CTkButton):
    """Botão secundário, discreto, apenas com contorno."""

    def __init__(self, master: Any, text: str, command: Callable[[], None] | None = None,
                 **kwargs: Any) -> None:
        """Inicializa o botão secundário.

        Args:
            master: Widget pai.
            text: Rótulo exibido.
            command: Função chamada ao clicar.
            **kwargs: Parâmetros extras repassados ao ``CTkButton``.
        """
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", THEME.card_hover)
        kwargs.setdefault("text_color", THEME.text_secondary)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", THEME.border)
        kwargs.setdefault("corner_radius", THEME.radius)
        kwargs.setdefault("height", 40)
        kwargs.setdefault("font", font(THEME.size_body))
        super().__init__(master, text=text, command=command, **kwargs)


class OptionToggle(ctk.CTkFrame):
    """Linha com título, descrição curta e um interruptor."""

    def __init__(
        self,
        master: Any,
        title: str,
        description: str,
        initial: bool = False,
        command: Callable[[bool], None] | None = None,
    ) -> None:
        """Inicializa o interruptor de opção.

        Args:
            master: Widget pai.
            title: Nome da opção.
            description: Explicação em uma linha.
            initial: Estado inicial do interruptor.
            command: Callback chamado com o novo valor booleano.
        """
        super().__init__(master, fg_color="transparent")
        self._command = command
        self.variable = ctk.BooleanVar(value=initial)

        self.grid_columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            self,
            text=title,
            font=font(THEME.size_body),
            text_color=THEME.text,
            anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self._description_label = ctk.CTkLabel(
            self,
            text=description,
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        )
        self._description_label.grid(row=1, column=0, sticky="w")

        self.switch = ctk.CTkSwitch(
            self,
            text="",
            width=44,
            variable=self.variable,
            command=self._on_toggle,
            progress_color=THEME.primary,
            button_color=THEME.text,
            button_hover_color=THEME.text_secondary,
            fg_color=THEME.border,
        )
        self.switch.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

    def _on_toggle(self) -> None:
        """Repassa a mudança de estado ao callback informado."""
        if self._command is not None:
            self._command(bool(self.variable.get()))

    @property
    def value(self) -> bool:
        """Estado atual do interruptor."""
        return bool(self.variable.get())

    def set_enabled(self, enabled: bool) -> None:
        """Habilita ou desabilita o interruptor.

        Args:
            enabled: ``True`` para habilitar.
        """
        self.switch.configure(state="normal" if enabled else "disabled")

    def set_texts(self, title: str, description: str) -> None:
        """Atualiza o título e a descrição exibidos (ex.: troca de idioma).

        Args:
            title: Novo nome da opção.
            description: Nova explicação em uma linha.
        """
        self._title_label.configure(text=title)
        self._description_label.configure(text=description)


class SegmentedSelector(ctk.CTkFrame):
    """Seletor de opção única entre poucas alternativas nomeadas.

    Mostra um botão por opção (ex.: os modos de fundo, ou o formato de
    exportação) numa grade de colunas fixas, o suficiente pra caber com
    folga mesmo com a barra lateral estreitada, e destaca a opção ativa.
    """

    def __init__(
        self,
        master: Any,
        modes: tuple[str, ...],
        labels: dict[str, str],
        command: Callable[[str], None] | None = None,
        initial: str = "transparent",
        columns: int = 2,
    ) -> None:
        """Inicializa o seletor.

        Args:
            master: Widget pai.
            modes: Chaves internas das opções disponíveis, na ordem de exibição.
            labels: Rótulo exibido para cada chave de ``modes``.
            command: Callback chamado com a chave da opção escolhida.
            initial: Opção inicialmente selecionada.
            columns: Número de colunas da grade de botões.
        """
        super().__init__(master, fg_color="transparent")
        self._command = command
        self._active = initial
        self._modes = modes
        self._columns = max(1, columns)
        self._buttons: dict[str, ctk.CTkButton] = {}

        for column in range(self._columns):
            self.grid_columnconfigure(column, weight=1, uniform="segmented")

        for index, key in enumerate(modes):
            row, column = divmod(index, self._columns)
            button = ctk.CTkButton(
                self,
                text=labels.get(key, key),
                height=30,
                corner_radius=8,
                fg_color=THEME.primary if key == initial else THEME.surface,
                hover_color=THEME.primary_hover if key == initial else THEME.card_hover,
                text_color=THEME.text if key == initial else THEME.text_secondary,
                font=font(THEME.size_small),
                command=lambda k=key: self._select(k),
            )
            button.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 4, 0),
                pady=(0 if row == 0 else 4, 0),
            )
            self._buttons[key] = button

    def set_labels(self, labels: dict[str, str]) -> None:
        """Atualiza os textos dos botões (ex.: troca de idioma).

        Args:
            labels: Rótulo exibido para cada chave de modo conhecida.
        """
        for key, button in self._buttons.items():
            if key in labels:
                button.configure(text=labels[key])

    def _select(self, key: str) -> None:
        """Ativa um modo e repassa a escolha ao callback.

        Args:
            key: Chave do modo escolhido.
        """
        self._active = key
        for candidate, button in self._buttons.items():
            active = candidate == key
            button.configure(
                fg_color=THEME.primary if active else THEME.surface,
                hover_color=THEME.primary_hover if active else THEME.card_hover,
                text_color=THEME.text if active else THEME.text_secondary,
            )
        if self._command is not None:
            self._command(key)

    def set_enabled(self, enabled: bool) -> None:
        """Habilita ou desabilita todos os botões do seletor.

        Args:
            enabled: ``True`` para habilitar.
        """
        state = "normal" if enabled else "disabled"
        for button in self._buttons.values():
            button.configure(state=state)

    @property
    def value(self) -> str:
        """Chave do modo atualmente selecionado."""
        return self._active


class LabeledSlider(ctk.CTkFrame):
    """Slider com rótulo e valor numérico, para ajustes finos em tempo real.

    O ``command`` é chamado continuamente enquanto o usuário arrasta, então é
    ideal para pré-visualizações ao vivo (ex.: intensidade de um desfoque).
    """

    def __init__(
        self,
        master: Any,
        label: str,
        from_: float,
        to: float,
        initial: float,
        command: Callable[[float], None] | None = None,
        value_format: str = "{:.1f}",
    ) -> None:
        """Inicializa o slider.

        Args:
            master: Widget pai.
            label: Texto exibido à esquerda, acima da barra.
            from_: Valor mínimo.
            to: Valor máximo.
            initial: Valor inicial.
            command: Callback chamado com o novo valor a cada movimento.
            value_format: Máscara usada para exibir o valor atual (ex.:
                ``"{:.0f}px"``).
        """
        super().__init__(master, fg_color="transparent")
        self._command = command
        self._value_format = value_format
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self._label = ctk.CTkLabel(
            header, text=label, font=font(THEME.size_small),
            text_color=THEME.text_secondary, anchor="w",
        )
        self._label.grid(row=0, column=0, sticky="w")

        self._value_label = ctk.CTkLabel(
            header, text=value_format.format(initial),
            font=font(THEME.size_small), text_color=THEME.text_muted,
        )
        self._value_label.grid(row=0, column=1, sticky="e")

        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            progress_color=THEME.primary,
            button_color=THEME.text,
            button_hover_color=THEME.text_secondary,
            fg_color=THEME.border,
            command=self._on_change,
        )
        self.slider.set(initial)
        self.slider.grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _on_change(self, value: float) -> None:
        """Atualiza o rótulo de valor e repassa a mudança ao callback."""
        self._value_label.configure(text=self._value_format.format(value))
        if self._command is not None:
            self._command(float(value))

    def set_label(self, text: str) -> None:
        """Atualiza o rótulo exibido (ex.: troca de idioma).

        Args:
            text: Novo texto do rótulo.
        """
        self._label.configure(text=text)

    def set_enabled(self, enabled: bool) -> None:
        """Habilita ou desabilita o slider.

        Args:
            enabled: ``True`` para habilitar.
        """
        self.slider.configure(state="normal" if enabled else "disabled")

    @property
    def value(self) -> float:
        """Valor atual do slider."""
        return float(self.slider.get())


class ProgressPanel(ctk.CTkFrame):
    """Barra de progresso com rótulo de status, exibida somente durante o trabalho."""

    def __init__(self, master: Any) -> None:
        """Inicializa o painel de progresso.

        Args:
            master: Widget pai.
        """
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            self,
            text="",
            font=font(THEME.size_small),
            text_color=THEME.text_secondary,
            anchor="w",
        )
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.bar = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            fg_color=THEME.border,
            progress_color=THEME.primary,
        )
        self.bar.grid(row=1, column=0, sticky="ew")
        self.bar.set(0)

    def start_indeterminate(self, message: str) -> None:
        """Exibe uma animação contínua para tarefas sem progresso mensurável.

        Args:
            message: Texto exibido acima da barra.
        """
        self.label.configure(text=message)
        self.bar.configure(mode="indeterminate")
        self.bar.start()

    def set_progress(self, current: int, total: int, message: str) -> None:
        """Atualiza a barra com o progresso de um lote.

        Args:
            current: Índice da imagem atual (base 1).
            total: Quantidade total de imagens.
            message: Texto exibido acima da barra.
        """
        self.bar.stop()
        self.bar.configure(mode="determinate")
        self.bar.set(current / total if total else 0)
        self.label.configure(text=message)

    def stop(self) -> None:
        """Interrompe a animação e zera a barra."""
        self.bar.stop()
        self.bar.configure(mode="determinate")
        self.bar.set(0)
        self.label.configure(text="")


class StatusBar(ctk.CTkFrame):
    """Rodapé com a versão do app, um indicador colorido e uma mensagem curta."""

    def __init__(self, master: Any, version: str = "") -> None:
        """Inicializa a barra de status.

        Args:
            master: Widget pai.
            version: Texto de versão exibido no canto esquerdo (ex.: ``"v1.0.0"``).
                Omitido se vazio.
        """
        super().__init__(master, fg_color="transparent", height=26)

        self.link_label: LinkLabel | None = None
        if version:
            self.link_label = LinkLabel(
                self,
                DEVELOPER_NAME,
                DEVELOPER_URL,
                font=font(THEME.size_small),
                text_color=THEME.primary,
            )
            self.link_label.pack(side="right", padx=(0, 12))
        

        self.version_label: ctk.CTkLabel | None = None
        if version:
            self.version_label = ctk.CTkLabel(
                self,
                text=version,
                font=font(THEME.size_small),
                text_color=THEME.text_muted,
            )
            self.version_label.pack(side="right", padx=(0, 12))

        
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            width=14,
        )
        self.dot.pack(side="left")

        self.message = ctk.CTkLabel(
            self,
            text="Pronto",
            font=font(THEME.size_small),
            text_color=THEME.text_secondary,
            anchor="w",
        )
        self.message.pack(side="left", padx=(4, 0))

    def show(self, text: str, level: str = "info") -> None:
        """Atualiza a mensagem exibida.

        Args:
            text: Texto da mensagem.
            level: Um de ``"info"``, ``"success"``, ``"warning"`` ou ``"error"``.
        """
        colors = {
            "info": THEME.text_muted,
            "success": THEME.success,
            "warning": THEME.warning,
            "error": THEME.danger,
        }
        self.dot.configure(text_color=colors.get(level, THEME.text_muted))
        self.message.configure(text=text)


class FileList(ctk.CTkScrollableFrame):
    """Lista rolável com os arquivos da fila de processamento."""

    def __init__(self, master: Any, on_select: Callable[[int], None] | None = None) -> None:
        """Inicializa a lista de arquivos.

        Args:
            master: Widget pai.
            on_select: Callback recebendo o índice do item clicado.
        """
        super().__init__(
            master,
            fg_color=THEME.surface,
            corner_radius=THEME.radius,
            scrollbar_button_color=THEME.border,
            scrollbar_button_hover_color=THEME.text_muted,
        )
        self._on_select = on_select
        self._buttons: list[ctk.CTkButton] = []
        self._names: list[str] = []
        self._marks: list[str] = []
        self.grid_columnconfigure(0, weight=1)

    def set_items(self, names: list[str], selected: int = 0) -> None:
        """Substitui o conteúdo da lista.

        Args:
            names: Nomes dos arquivos a exibir.
            selected: Índice do item destacado.
        """
        for button in self._buttons:
            button.destroy()
        self._buttons.clear()
        self._names = list(names)
        self._marks = ["" for _ in names]

        for index, name in enumerate(names):
            button = ctk.CTkButton(
                self,
                text=f"  {name}",
                anchor="w",
                height=32,
                corner_radius=8,
                fg_color=THEME.card if index == selected else "transparent",
                hover_color=THEME.card_hover,
                text_color=THEME.text if index == selected else THEME.text_secondary,
                font=font(THEME.size_small),
                command=lambda i=index: self._select(i),
            )
            button.grid(row=index, column=0, sticky="ew", pady=2, padx=4)
            self._buttons.append(button)

    def highlight(self, index: int) -> None:
        """Destaca visualmente um item da lista.

        Preserva a cor de status (concluído/erro) de itens já processados,
        mesmo quando eles não estão selecionados.

        Args:
            index: Índice do item a destacar.
        """
        mark_colors = {"✓": THEME.success, "!": THEME.danger}
        for position, button in enumerate(self._buttons):
            active = position == index
            mark = self._marks[position] if position < len(self._marks) else ""
            default_color = THEME.text if active else THEME.text_secondary
            button.configure(
                fg_color=THEME.card if active else "transparent",
                text_color=mark_colors.get(mark, default_color),
            )

    def _label_for(self, index: int) -> str:
        """Monta o texto exibido para um item, incluindo seu marcador de status.

        Args:
            index: Índice do item.

        Returns:
            Texto pronto para o botão da lista.
        """
        mark = self._marks[index] if index < len(self._marks) else ""
        prefix = f"{mark} " if mark else "  "
        return f"{prefix}{self._names[index]}"

    def mark_done(self, index: int) -> None:
        """Sinaliza que um item já foi processado com sucesso.

        Args:
            index: Índice do item concluído.
        """
        if not (0 <= index < len(self._buttons)):
            return
        self._marks[index] = "✓"
        self._buttons[index].configure(text=self._label_for(index), text_color=THEME.success)

    def mark_error(self, index: int) -> None:
        """Sinaliza que o processamento de um item falhou.

        Args:
            index: Índice do item com erro.
        """
        if not (0 <= index < len(self._buttons)):
            return
        self._marks[index] = "!"
        self._buttons[index].configure(text=self._label_for(index), text_color=THEME.danger)

    def _select(self, index: int) -> None:
        """Trata o clique em um item.

        Args:
            index: Índice clicado.
        """
        self.highlight(index)
        if self._on_select is not None:
            self._on_select(index)
