"""Configurações globais da aplicação.

Centraliza cores, fontes, formatos suportados e parâmetros dos modelos de IA
para que nenhum valor mágico fique espalhado pelo restante do código.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Caminhos
# --------------------------------------------------------------------------- #


def resource_path(relative: str) -> Path:
    """Resolve o caminho de um recurso em dev e dentro do executável PyInstaller.

    Args:
        relative: Caminho relativo à raiz do projeto (ex.: ``"assets/icon.ico"``).

    Returns:
        Caminho absoluto para o recurso.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
ICON_PATH: Path = resource_path("assets/icon.ico")
LOGO_PATH: Path = resource_path("assets/logo.png")


# --------------------------------------------------------------------------- #
# Aparência
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Theme:
    """Paleta de cores e métricas visuais do aplicativo."""

    # Cores base
    background: str = "#1E1E1E"
    card: str = "#2B2B2B"
    card_hover: str = "#333333"
    surface: str = "#242424"
    border: str = "#3A3A3A"

    # Ação
    primary: str = "#3B82F6"
    primary_hover: str = "#2563EB"
    primary_disabled: str = "#2F4C7A"

    # Texto
    text: str = "#FFFFFF"
    text_secondary: str = "#B3B3B3"
    text_muted: str = "#7A7A7A"

    # Estados
    success: str = "#22C55E"
    warning: str = "#F59E0B"
    danger: str = "#EF4444"

    # Xadrez de transparência
    checker_light: str = "#3C3C3C"
    checker_dark: str = "#323232"

    # Métricas
    radius: int = 12
    radius_large: int = 16
    padding: int = 20
    gap: int = 14

    # Tipografia
    font_family: str = "Segoe UI"
    size_title: int = 20
    size_subtitle: int = 13
    size_body: int = 13
    size_small: int = 11


THEME = Theme()


# --------------------------------------------------------------------------- #
# Imagens e modelos
# --------------------------------------------------------------------------- #

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")

FILE_DIALOG_TYPES: list[tuple[str, str]] = [
    ("Imagens", "*.png *.jpg *.jpeg *.webp"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("WEBP", "*.webp"),
    ("Todos os arquivos", "*.*"),
]

#: Modelo principal e fallback usados pelo ``rembg``.
PRIMARY_MODEL: str = "isnet-general-use"
FALLBACK_MODEL: str = "u2net"

#: Tamanho máximo (em pixels) de cada lado na pré-visualização.
PREVIEW_MAX_SIZE: int = 560

#: Sufixo aplicado aos arquivos exportados.
EXPORT_SUFFIX: str = "_sem_fundo"

APP_NAME: str = "Removedor de Fundo IA"
APP_VERSION: str = "1.0.0"
WINDOW_SIZE: tuple[int, int] = (1180, 780)
WINDOW_MIN_SIZE: tuple[int, int] = (980, 660)


@dataclass
class ProcessingOptions:
    """Opções de pós-processamento aplicadas após a remoção do fundo.

    Attributes:
        auto_crop: Recorta automaticamente as bordas totalmente transparentes.
        refine_edges: Remove o halo claro deixado ao redor do recorte.
        smooth_contour: Suaviza o contorno do canal alfa.
        keep_resolution: Mantém a resolução original da imagem de entrada.
        smooth_radius: Intensidade da suavização do contorno.
    """

    auto_crop: bool = False
    refine_edges: bool = True
    smooth_contour: bool = True
    keep_resolution: bool = True
    smooth_radius: float = 1.0

    def as_dict(self) -> dict[str, object]:
        """Retorna as opções em formato de dicionário."""
        return {
            "auto_crop": self.auto_crop,
            "refine_edges": self.refine_edges,
            "smooth_contour": self.smooth_contour,
            "keep_resolution": self.keep_resolution,
            "smooth_radius": self.smooth_radius,
        }


@dataclass
class JobResult:
    """Resultado do processamento de uma única imagem.

    Attributes:
        source: Caminho da imagem de origem.
        output: Caminho do PNG exportado (``None`` se ainda não salvo).
        success: Indica se o processamento terminou sem erros.
        message: Mensagem amigável de erro, quando aplicável.
    """

    source: Path
    output: Path | None = None
    success: bool = True
    message: str = ""


@dataclass
class BatchReport:
    """Resumo de um processamento em lote."""

    results: list[JobResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Quantidade total de imagens processadas."""
        return len(self.results)

    @property
    def succeeded(self) -> int:
        """Quantidade de imagens processadas com sucesso."""
        return sum(1 for item in self.results if item.success)

    @property
    def failed(self) -> int:
        """Quantidade de imagens que falharam."""
        return self.total - self.succeeded

    @property
    def failures(self) -> list[JobResult]:
        """Lista apenas dos resultados que falharam."""
        return [item for item in self.results if not item.success]
