"""Pré-visualização antes/depois das imagens."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk
from PIL import Image

from config import THEME
from services.image_processor import ImageProcessor
from ui.components import font


class PreviewPane(ctk.CTkFrame):
    """Um lado da pré-visualização, com título e área de imagem.

    A imagem é redesenhada sempre que o painel muda de tamanho, de modo que a
    janela pode ser redimensionada livremente sem distorcer o conteúdo.
    """

    def __init__(
        self,
        master: Any,
        title: str,
        placeholder: str,
        transparent_background: bool = False,
    ) -> None:
        """Inicializa o painel.

        Args:
            master: Widget pai.
            title: Título exibido no topo (ex.: "Antes").
            placeholder: Texto mostrado quando não há imagem.
            transparent_background: Se ``True``, desenha o xadrez de
                transparência atrás da imagem.
        """
        super().__init__(master, fg_color=THEME.surface, corner_radius=THEME.radius)

        self._title = title
        self._placeholder = placeholder
        self._transparent_background = transparent_background
        self._image: Image.Image | None = None
        self._ctk_image: ctk.CTkImage | None = None
        self._render_job: str | None = None
        self._last_size: tuple[int, int] = (0, 0)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkLabel(
            self,
            text=title,
            font=font(THEME.size_small, "bold"),
            text_color=THEME.text_secondary,
            anchor="w",
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        self.canvas = ctk.CTkLabel(
            self,
            text=placeholder,
            font=font(THEME.size_body),
            text_color=THEME.text_muted,
            image=None,
            wraplength=260,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 14))

        self.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #

    def set_image(self, image: Image.Image | None) -> None:
        """Define (ou remove) a imagem exibida.

        Args:
            image: Imagem a exibir, ou ``None`` para voltar ao estado vazio.
        """
        self._image = image
        if image is None:
            self._ctk_image = None
            self.canvas.configure(image=None, text=self._placeholder)
            self.set_subtitle("")
            return
        self._render()

    def set_subtitle(self, text: str) -> None:
        """Atualiza o texto do cabeçalho com uma informação extra.

        Args:
            text: Informação adicional (ex.: "1920 × 1080").
        """
        self.header.configure(text=self._title if not text else f"{self._title}   ·   {text}")

    def clear(self) -> None:
        """Volta o painel ao estado vazio."""
        self.set_image(None)

    # ------------------------------------------------------------------ #
    # Renderização
    # ------------------------------------------------------------------ #

    def _on_resize(self, _event: Any) -> None:
        """Reagenda a renderização quando o painel muda de tamanho."""
        if self._image is None:
            return
        if self._render_job is not None:
            self.after_cancel(self._render_job)
        self._render_job = self.after(90, self._render)

    def _available_size(self) -> tuple[int, int]:
        """Calcula o espaço útil disponível para a imagem.

        Returns:
            Par ``(largura, altura)`` em pixels.
        """
        width = max(self.winfo_width() - 32, 120)
        height = max(self.winfo_height() - 60, 120)
        return width, height

    def _render(self) -> None:
        """Redimensiona e desenha a imagem atual dentro do painel."""
        self._render_job = None
        image = self._image
        if image is None:
            return

        box_width, box_height = self._available_size()
        scale = min(box_width / image.width, box_height / image.height, 1.0)
        target = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))

        resized = image.resize(target, Image.LANCZOS)
        if self._transparent_background:
            resized = ImageProcessor.flatten_on_checkerboard(
                resized, THEME.checker_light, THEME.checker_dark
            )

        self._ctk_image = ctk.CTkImage(light_image=resized, dark_image=resized, size=target)
        self.canvas.configure(image=self._ctk_image, text="")
        self._last_size = target


class PreviewArea(ctk.CTkFrame):
    """Área central com as pré-visualizações "Antes" e "Depois" lado a lado."""

    def __init__(self, master: Any) -> None:
        """Inicializa a área de pré-visualização.

        Args:
            master: Widget pai.
        """
        super().__init__(master, fg_color="transparent")

        self.grid_columnconfigure((0, 2), weight=1, uniform="preview")
        self.grid_rowconfigure(0, weight=1)

        self.before = PreviewPane(
            self,
            title="Antes",
            placeholder="Arraste uma imagem aqui\nou clique em “Selecionar imagens”",
        )
        self.before.grid(row=0, column=0, sticky="nsew")

        self.after_pane = PreviewPane(
            self,
            title="Depois",
            placeholder="O resultado aparece aqui",
            transparent_background=True,
        )
        self.after_pane.grid(row=0, column=2, sticky="nsew")

        spacer = ctk.CTkFrame(self, fg_color="transparent", width=THEME.gap)
        spacer.grid(row=0, column=1, sticky="ns")

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #

    def show_original(self, image: Image.Image) -> None:
        """Exibe a imagem original no painel "Antes".

        Args:
            image: Imagem carregada do disco.
        """
        self.before.set_image(image)
        self.before.set_subtitle(f"{image.width} × {image.height}")

    def show_result(self, image: Image.Image) -> None:
        """Exibe o recorte no painel "Depois".

        Args:
            image: Imagem processada.
        """
        self.after_pane.set_image(image)
        self.after_pane.set_subtitle(f"{image.width} × {image.height}  ·  PNG")

    def clear_result(self) -> None:
        """Limpa apenas o painel de resultado."""
        self.after_pane.clear()

    def clear(self) -> None:
        """Limpa os dois painéis."""
        self.before.clear()
        self.after_pane.clear()
