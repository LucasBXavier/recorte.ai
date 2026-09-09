"""Carregamento, validação e pós-processamento de imagens."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter, UnidentifiedImageError

from config import PREVIEW_MAX_SIZE, SUPPORTED_EXTENSIONS, ProcessingOptions
from services.errors import CorruptedFileError, InvalidImageError

#: Evita o aviso de "decompression bomb" travar imagens grandes legítimas.
Image.MAX_IMAGE_PIXELS = None


class ImageProcessor:
    """Operações de imagem independentes da interface gráfica."""

    # ------------------------------------------------------------------ #
    # Entrada
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_supported(path: Path | str) -> bool:
        """Informa se a extensão do arquivo é aceita pelo aplicativo.

        Args:
            path: Caminho do arquivo.

        Returns:
            ``True`` quando a extensão está em :data:`SUPPORTED_EXTENSIONS`.
        """
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    @staticmethod
    def load(path: Path | str) -> Image.Image:
        """Carrega uma imagem do disco com validação amigável.

        Args:
            path: Caminho do arquivo de imagem.

        Returns:
            Imagem carregada em modo ``RGBA``.

        Raises:
            InvalidImageError: Arquivo inexistente ou formato não suportado.
            CorruptedFileError: Arquivo ilegível, truncado ou corrompido.
        """
        file_path = Path(path)

        if not file_path.exists():
            raise InvalidImageError(
                f"O arquivo não foi encontrado:\n{file_path.name}",
                detail=str(file_path),
            )

        if not ImageProcessor.is_supported(file_path):
            supported = ", ".join(ext.upper().lstrip(".") for ext in SUPPORTED_EXTENSIONS)
            raise InvalidImageError(
                f"Formato não suportado: {file_path.suffix or 'sem extensão'}.\n"
                f"Use um destes formatos: {supported}.",
                detail=str(file_path),
            )

        try:
            with Image.open(file_path) as opened:
                opened.load()
                image = opened.convert("RGBA")
        except UnidentifiedImageError as exc:
            raise CorruptedFileError(
                f"Não foi possível ler a imagem:\n{file_path.name}\n"
                "O arquivo pode estar corrompido ou não ser uma imagem válida.",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise CorruptedFileError(
                f"O arquivo parece estar corrompido ou incompleto:\n{file_path.name}",
                detail=str(exc),
            ) from exc

        return image

    # ------------------------------------------------------------------ #
    # Pós-processamento
    # ------------------------------------------------------------------ #

    @staticmethod
    def refine_edges(image: Image.Image) -> Image.Image:
        """Reduz o halo claro que costuma sobrar ao redor do recorte.

        A técnica encolhe levemente a máscara alfa e reaplica um leve ganho de
        contraste, eliminando pixels semitransparentes herdados do fundo.

        Args:
            image: Imagem ``RGBA`` já com fundo removido.

        Returns:
            Nova imagem com o canal alfa refinado.
        """
        result = image.copy()
        alpha = result.getchannel("A")
        eroded = alpha.filter(ImageFilter.MinFilter(3))
        # Mistura suave entre a máscara original e a erodida: remove o halo sem
        # comer detalhes finos como cabelo.
        blended = Image.blend(alpha, eroded, 0.55)
        contrasted = blended.point(lambda value: 0 if value < 8 else min(255, int(value * 1.06)))
        result.putalpha(contrasted)
        return result

    @staticmethod
    def smooth_contour(image: Image.Image, radius: float = 1.0) -> Image.Image:
        """Suaviza o contorno do recorte aplicando desfoque no canal alfa.

        Args:
            image: Imagem ``RGBA`` já com fundo removido.
            radius: Raio do desfoque gaussiano. Valores maiores suavizam mais.

        Returns:
            Nova imagem com o contorno suavizado.
        """
        if radius <= 0:
            return image

        result = image.copy()
        alpha = result.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
        result.putalpha(alpha)
        return result

    @staticmethod
    def auto_crop(image: Image.Image) -> Image.Image:
        """Recorta as bordas totalmente transparentes da imagem.

        Args:
            image: Imagem ``RGBA``.

        Returns:
            Imagem recortada, ou a original caso não haja o que recortar.
        """
        bbox = image.getchannel("A").getbbox()
        if bbox is None or bbox == (0, 0, image.width, image.height):
            return image
        return image.crop(bbox)

    # ------------------------------------------------------------------ #
    # Fundo
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
        """Redimensiona uma imagem para cobrir totalmente o tamanho alvo.

        Mantém a proporção original e recorta o excesso pelo centro, como o
        ``background-size: cover`` do CSS.

        Args:
            image: Imagem de origem.
            size: Dimensões ``(largura, altura)`` a cobrir.

        Returns:
            Imagem redimensionada e recortada com exatamente ``size``.
        """
        target_w, target_h = max(1, size[0]), max(1, size[1])
        scale = max(target_w / image.width, target_h / image.height)
        scaled = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.LANCZOS,
        )
        left = (scaled.width - target_w) // 2
        top = (scaled.height - target_h) // 2
        return scaled.crop((left, top, left + target_w, top + target_h))

    @staticmethod
    def apply_background(
        image: Image.Image,
        options: ProcessingOptions,
        original: Image.Image | None = None,
    ) -> Image.Image:
        """Compõe o recorte sobre o fundo escolhido pelo usuário.

        Args:
            image: Recorte ``RGBA`` já com os demais ajustes aplicados.
            options: Opções escolhidas na interface, incluindo o modo de fundo.
            original: Imagem original (antes da remoção de fundo), usada no
                modo ``"blur"``. Ignorada nos demais modos.

        Returns:
            Imagem final ``RGBA``. Continua transparente se o modo for
            ``"transparent"`` ou se um fundo customizado não puder ser
            carregado.
        """
        mode = options.background_mode

        if mode == "color":
            background = Image.new("RGBA", image.size, options.background_color)
        elif mode == "blur":
            base = original if original is not None else image
            base = base.convert("RGB")
            if base.size != image.size:
                base = ImageProcessor._cover_resize(base, image.size)
            radius = max(0.0, options.background_blur_radius)
            background = base.filter(ImageFilter.GaussianBlur(radius)).convert("RGBA")
        elif mode == "image" and options.background_image_path:
            try:
                with Image.open(options.background_image_path) as opened:
                    custom = opened.convert("RGB")
                    custom.load()
            except (OSError, UnidentifiedImageError):
                return image
            background = ImageProcessor._cover_resize(custom, image.size).convert("RGBA")
        else:
            return image

        background.alpha_composite(image)
        return background

    # ------------------------------------------------------------------ #
    # Exportação
    # ------------------------------------------------------------------ #

    @staticmethod
    def resize_to_max(image: Image.Image, max_size: int) -> Image.Image:
        """Redimensiona a imagem para que o maior lado não ultrapasse ``max_size``.

        Nunca amplia a imagem, apenas encolhe quando necessário.

        Args:
            image: Imagem a redimensionar.
            max_size: Maior dimensão permitida, em pixels. ``0`` ou negativo
                significa "sem limite".

        Returns:
            Imagem redimensionada mantendo a proporção, ou a original se já
            estiver dentro do limite.
        """
        if max_size <= 0:
            return image

        longest = max(image.width, image.height)
        if longest <= max_size:
            return image

        scale = max_size / longest
        target = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        return image.resize(target, Image.LANCZOS)

    @staticmethod
    def apply_options(
        image: Image.Image,
        options: ProcessingOptions,
        original_size: tuple[int, int] | None = None,
        original_image: Image.Image | None = None,
    ) -> Image.Image:
        """Aplica, na ordem correta, todos os ajustes selecionados pelo usuário.

        Args:
            image: Resultado bruto da remoção de fundo.
            options: Opções escolhidas na interface.
            original_size: Resolução da imagem original, usada quando
                ``options.keep_resolution`` está ativo.
            original_image: Imagem original antes da remoção de fundo, usada
                pelo modo de fundo ``"blur"``.

        Returns:
            Imagem final pronta para exportação.
        """
        result = image
        original = original_image

        if options.keep_resolution and original_size and result.size != original_size:
            result = result.resize(original_size, Image.LANCZOS)
            if original is not None and original.size != original_size:
                original = original.resize(original_size, Image.LANCZOS)

        if options.refine_edges:
            result = ImageProcessor.refine_edges(result)

        if options.smooth_contour:
            result = ImageProcessor.smooth_contour(result, options.smooth_radius)

        if options.auto_crop:
            bbox = result.getchannel("A").getbbox()
            if bbox is not None and bbox != (0, 0, result.width, result.height):
                result = result.crop(bbox)
                if original is not None:
                    original = original.crop(bbox)

        result = ImageProcessor.apply_background(result, options, original)

        if options.resize_on_export:
            result = ImageProcessor.resize_to_max(result, options.export_max_size)

        return result

    # ------------------------------------------------------------------ #
    # Pré-visualização
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_thumbnail(image: Image.Image, max_size: int = PREVIEW_MAX_SIZE) -> Image.Image:
        """Cria uma cópia reduzida da imagem para exibição na tela.

        Args:
            image: Imagem de origem.
            max_size: Maior dimensão permitida, em pixels.

        Returns:
            Cópia redimensionada mantendo a proporção original.
        """
        thumb = image.copy()
        thumb.thumbnail((max_size, max_size), Image.LANCZOS)
        return thumb

    @staticmethod
    def checkerboard(
        size: tuple[int, int],
        light: str,
        dark: str,
        tile: int = 12,
    ) -> Image.Image:
        """Gera o padrão xadrez usado como fundo de áreas transparentes.

        Args:
            size: Dimensões ``(largura, altura)`` do padrão.
            light: Cor dos quadrados claros.
            dark: Cor dos quadrados escuros.
            tile: Tamanho de cada quadrado, em pixels.

        Returns:
            Imagem ``RGBA`` com o padrão xadrez.
        """
        width, height = max(1, size[0]), max(1, size[1])
        base = Image.new("RGBA", (width, height), light)
        square = Image.new("RGBA", (tile, tile), dark)

        for y in range(0, height, tile):
            for x in range(0, width, tile):
                if ((x // tile) + (y // tile)) % 2:
                    base.paste(square, (x, y))
        return base

    @staticmethod
    def flatten_on_checkerboard(
        image: Image.Image,
        light: str,
        dark: str,
        tile: int = 12,
    ) -> Image.Image:
        """Compõe a imagem transparente sobre um padrão xadrez.

        Args:
            image: Imagem ``RGBA``.
            light: Cor dos quadrados claros.
            dark: Cor dos quadrados escuros.
            tile: Tamanho de cada quadrado, em pixels.

        Returns:
            Imagem ``RGBA`` opaca, pronta para exibição.
        """
        background = ImageProcessor.checkerboard(image.size, light, dark, tile)
        background.alpha_composite(image)
        return background
