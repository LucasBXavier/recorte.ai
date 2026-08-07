"""Componentes reutilizáveis da interface.

Todos seguem a paleta definida em :data:`config.THEME`, garantindo consistência
visual e evitando repetição de parâmetros de estilo pela aplicação.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from config import THEME


def font(size: int = THEME.size_body, weight: str = "normal") -> ctk.CTkFont:
    """Cria uma fonte padronizada do aplicativo.

    Args:
        size: Tamanho em pontos.
        weight: ``"normal"`` ou ``"bold"``.

    Returns:
        Objeto de fonte pronto para uso em widgets do CustomTkinter.
    """
    return ctk.CTkFont(family=THEME.font_family, size=size, weight=weight)


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

        ctk.CTkLabel(
            self,
            text=title,
            font=font(THEME.size_body),
            text_color=THEME.text,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            self,
            text=description,
            font=font(THEME.size_small),
            text_color=THEME.text_muted,
            anchor="w",
        ).grid(row=1, column=0, sticky="w")

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
    """Rodapé com um indicador colorido e uma mensagem curta."""

    def __init__(self, master: Any) -> None:
        """Inicializa a barra de status.

        Args:
            master: Widget pai.
        """
        super().__init__(master, fg_color="transparent", height=26)
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

        Args:
            index: Índice do item a destacar.
        """
        for position, button in enumerate(self._buttons):
            active = position == index
            button.configure(
                fg_color=THEME.card if active else "transparent",
                text_color=THEME.text if active else THEME.text_secondary,
            )

    def _select(self, index: int) -> None:
        """Trata o clique em um item.

        Args:
            index: Índice clicado.
        """
        self.highlight(index)
        if self._on_select is not None:
            self._on_select(index)
