"""Gravação dos resultados em disco."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from config import EXPORT_SUFFIX
from services.errors import ExportError

#: Extensão de arquivo para cada formato de exportação suportado.
_EXTENSIONS: dict[str, str] = {"png": ".png", "webp": ".webp"}


class ExportService:
    """Responsável por salvar os resultados com segurança, em PNG ou WEBP."""

    def __init__(self, suffix: str = EXPORT_SUFFIX, overwrite: bool = False) -> None:
        """Inicializa o serviço.

        Args:
            suffix: Sufixo acrescentado ao nome do arquivo exportado.
            overwrite: Quando ``False``, gera um nome único em vez de
                sobrescrever um arquivo existente.
        """
        self.suffix = suffix
        self.overwrite = overwrite

    # ------------------------------------------------------------------ #
    # Nomes de arquivo
    # ------------------------------------------------------------------ #

    def build_output_path(
        self, source: Path, destination_dir: Path, format: str = "png"
    ) -> Path:
        """Monta o caminho de saída para uma imagem de origem.

        Args:
            source: Caminho da imagem original.
            destination_dir: Pasta onde o arquivo será gravado.
            format: Formato de exportação (``"png"`` ou ``"webp"``).

        Returns:
            Caminho completo do arquivo de destino, já livre de colisões
            quando ``overwrite`` é ``False``.
        """
        extension = _EXTENSIONS.get(format, ".png")
        candidate = destination_dir / f"{source.stem}{self.suffix}{extension}"
        return candidate if self.overwrite else self.unique_path(candidate)

    @staticmethod
    def unique_path(path: Path) -> Path:
        """Evita sobrescrever arquivos acrescentando um contador ao nome.

        Args:
            path: Caminho desejado.

        Returns:
            O próprio caminho, se estiver livre, ou uma variação numerada.
        """
        if not path.exists():
            return path

        counter = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    # ------------------------------------------------------------------ #
    # Gravação
    # ------------------------------------------------------------------ #

    def _save_as(
        self,
        image: Image.Image,
        destination: Path,
        pillow_format: str,
        extension: str,
        **save_kwargs: object,
    ) -> Path:
        """Grava a imagem em um formato específico, com tratamento de erros comum.

        Args:
            image: Imagem a ser gravada.
            destination: Caminho completo do arquivo de destino.
            pillow_format: Nome do formato para o Pillow (``"PNG"``, ``"WEBP"``).
            extension: Extensão de arquivo esperada (com o ponto, ex.: ``".png"``).
            **save_kwargs: Parâmetros extras repassados a ``Image.save``.

        Returns:
            O caminho efetivamente utilizado.

        Raises:
            ExportError: Quando a pasta não pode ser criada ou a gravação falha
                por permissão, disco cheio ou caminho inválido.
        """
        target = Path(destination)
        if target.suffix.lower() != extension:
            target = target.with_suffix(extension)

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ExportError(
                f"Não foi possível criar a pasta de destino:\n{target.parent}",
                detail=str(exc),
            ) from exc

        payload = image if image.mode == "RGBA" else image.convert("RGBA")

        try:
            payload.save(target, format=pillow_format, **save_kwargs)
        except PermissionError as exc:
            raise ExportError(
                f"Sem permissão para salvar em:\n{target}\n"
                "Feche o arquivo se ele estiver aberto ou escolha outra pasta.",
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise ExportError(
                f"Não foi possível salvar a imagem:\n{target.name}\n"
                "Verifique o espaço em disco e tente novamente.",
                detail=str(exc),
            ) from exc

        return target

    def save_png(self, image: Image.Image, destination: Path) -> Path:
        """Salva a imagem como PNG com canal alfa preservado.

        Args:
            image: Imagem a ser gravada.
            destination: Caminho completo do arquivo de destino.

        Returns:
            O caminho efetivamente utilizado.

        Raises:
            ExportError: Quando a pasta não pode ser criada ou a gravação falha
                por permissão, disco cheio ou caminho inválido.
        """
        return self._save_as(image, destination, "PNG", ".png", optimize=True)

    def save_webp(self, image: Image.Image, destination: Path, quality: int = 90) -> Path:
        """Salva a imagem como WEBP com canal alfa preservado.

        Args:
            image: Imagem a ser gravada.
            destination: Caminho completo do arquivo de destino.
            quality: Qualidade da compressão (1-100). Valores menores geram
                arquivos menores, com mais perda visual.

        Returns:
            O caminho efetivamente utilizado.

        Raises:
            ExportError: Quando a pasta não pode ser criada ou a gravação falha
                por permissão, disco cheio ou caminho inválido.
        """
        return self._save_as(image, destination, "WEBP", ".webp", quality=quality)

    def save_image(
        self, image: Image.Image, destination: Path, format: str = "png", quality: int = 90
    ) -> Path:
        """Salva a imagem no formato indicado.

        Args:
            image: Imagem a ser gravada.
            destination: Caminho completo do arquivo de destino.
            format: Formato de exportação (``"png"`` ou ``"webp"``).
            quality: Qualidade da compressão, usada apenas para ``"webp"``.

        Returns:
            O caminho efetivamente utilizado.

        Raises:
            ExportError: Quando a pasta não pode ser criada ou a gravação falha
                por permissão, disco cheio ou caminho inválido.
        """
        if format == "webp":
            return self.save_webp(image, destination, quality=quality)
        return self.save_png(image, destination)

    def export(
        self,
        image: Image.Image,
        source: Path,
        destination_dir: Path,
        format: str = "png",
        quality: int = 90,
    ) -> Path:
        """Exporta a imagem para uma pasta, derivando o nome da origem.

        Args:
            image: Imagem processada.
            source: Caminho da imagem original (usado para nomear a saída).
            destination_dir: Pasta de destino.
            format: Formato de exportação (``"png"`` ou ``"webp"``).
            quality: Qualidade da compressão, usada apenas para ``"webp"``.

        Returns:
            Caminho do arquivo gravado.

        Raises:
            ExportError: Se a gravação falhar.
        """
        destination = self.build_output_path(source, Path(destination_dir), format=format)
        return self.save_image(image, destination, format=format, quality=quality)
