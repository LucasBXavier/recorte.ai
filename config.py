"""Configurações globais da aplicação.

Centraliza cores, fontes, formatos suportados e parâmetros dos modelos de IA
para que nenhum valor mágico fique espalhado pelo restante do código.
"""

from __future__ import annotations

import os
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


def _user_data_dir() -> Path:
    """Resolve uma pasta gravável do usuário para guardar preferências.

    Usa ``%APPDATA%`` no Windows (com um fallback para a pasta do usuário em
    outros sistemas), já que a pasta do executável pode estar em um diretório
    temporário somente leitura quando empacotado com o PyInstaller.

    Returns:
        Pasta onde o arquivo de preferências deve ser lido/gravado.
    """
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home()
    return root / "RecorteAI"


#: Arquivo com as preferências persistentes do usuário (idioma, layout).
PREFERENCES_PATH: Path = _user_data_dir() / "preferences.json"


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

#: Modelo principal e fallback usados pelo ``rembg``.
PRIMARY_MODEL: str = "isnet-general-use"
FALLBACK_MODEL: str = "u2net"

#: Parâmetros de "alpha matting" (pymatting) usados na remoção de fundo.
#: Refinam a máscara bruta do modelo com base nas cores reais da imagem,
#: melhorando a precisão em bordas complexas como cabelo e pelos.
ALPHA_MATTING_FOREGROUND_THRESHOLD: int = 240
ALPHA_MATTING_BACKGROUND_THRESHOLD: int = 15
ALPHA_MATTING_ERODE_SIZE: int = 8

#: Tamanho máximo (em pixels) de cada lado na pré-visualização.
PREVIEW_MAX_SIZE: int = 560

#: Sufixo aplicado aos arquivos exportados.
EXPORT_SUFFIX: str = "_sem_fundo"

#: Chaves internas dos modos de fundo disponíveis para o resultado final. Os
#: rótulos exibidos vêm do módulo :mod:`i18n`, para suportar troca de idioma.
BACKGROUND_MODE_KEYS: tuple[str, ...] = ("transparent", "color", "image", "blur")

#: Formatos de arquivo disponíveis para exportação.
EXPORT_FORMATS: tuple[str, ...] = ("png", "webp")

APP_NAME: str = "Recorte.ai"
APP_VERSION: str = "1.0.0"
WINDOW_SIZE: tuple[int, int] = (1180, 840)
WINDOW_MIN_SIZE: tuple[int, int] = (980, 700)

#: Créditos exibidos na janela de Ajuda, com link para o site do autor.
DEVELOPER_NAME: str = "Lucas Boareto"
DEVELOPER_URL: str = "https://lucasboareto.vercel.app"

# --------------------------------------------------------------------------- #
# Layout responsivo
# --------------------------------------------------------------------------- #

#: Largura inicial da barra lateral, em pixels (ajustável arrastando o divisor).
SIDEBAR_DEFAULT_WIDTH: int = 330
SIDEBAR_MIN_WIDTH: int = 260
SIDEBAR_MAX_WIDTH: int = 560
#: Espaço mínimo reservado para a área de pré-visualização.
MAIN_AREA_MIN_WIDTH: int = 380
#: Largura da faixa divisória arrastável entre a barra lateral e a pré-visualização.
SPLITTER_WIDTH: int = 10


@dataclass
class ProcessingOptions:
    """Opções de pós-processamento aplicadas após a remoção do fundo.

    Attributes:
        auto_crop: Recorta automaticamente as bordas totalmente transparentes.
        refine_edges: Remove o halo claro deixado ao redor do recorte.
        smooth_contour: Suaviza o contorno do canal alfa.
        keep_resolution: Mantém a resolução original da imagem de entrada.
        smooth_radius: Intensidade da suavização do contorno.
        background_mode: ``"transparent"``, ``"color"``, ``"image"`` ou ``"blur"``.
        background_color: Cor usada quando ``background_mode`` é ``"color"``.
        background_image_path: Caminho da imagem usada quando ``background_mode``
            é ``"image"``.
        background_blur_radius: Intensidade do desfoque quando ``background_mode``
            é ``"blur"``.
        export_format: Formato do arquivo exportado (``"png"`` ou ``"webp"``).
        export_quality: Qualidade de compressão do WEBP (1-100).
        resize_on_export: Se ``True``, limita o maior lado ao exportar.
        export_max_size: Maior lado permitido (em pixels) quando
            ``resize_on_export`` está ativo.
    """

    auto_crop: bool = False
    refine_edges: bool = True
    smooth_contour: bool = True
    keep_resolution: bool = True
    smooth_radius: float = 1.0
    background_mode: str = "transparent"
    background_color: str = "#FFFFFF"
    background_image_path: str | None = None
    background_blur_radius: float = 18.0
    export_format: str = "png"
    export_quality: int = 90
    resize_on_export: bool = False
    export_max_size: int = 1920

    def as_dict(self) -> dict[str, object]:
        """Retorna as opções em formato de dicionário."""
        return {
            "auto_crop": self.auto_crop,
            "refine_edges": self.refine_edges,
            "smooth_contour": self.smooth_contour,
            "keep_resolution": self.keep_resolution,
            "smooth_radius": self.smooth_radius,
            "background_mode": self.background_mode,
            "background_color": self.background_color,
            "background_image_path": self.background_image_path,
            "background_blur_radius": self.background_blur_radius,
            "export_format": self.export_format,
            "export_quality": self.export_quality,
            "resize_on_export": self.resize_on_export,
            "export_max_size": self.export_max_size,
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
