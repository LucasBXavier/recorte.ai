"""Gravação dos resultados em disco."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from config import EXPORT_SUFFIX
from services.errors import ExportError


class ExportService:
    """Responsável por salvar PNGs transparentes com segurança."""

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

    def build_output_path(self, source: Path, destination_dir: Path) -> Path:
        """Monta o caminho de saída para uma imagem de origem.

        Args:
            source: Caminho da imagem original.
            destination_dir: Pasta onde o PNG será gravado.

        Returns:
            Caminho completo do arquivo de destino, já livre de colisões
            quando ``overwrite`` é ``False``.
        """
        candidate = destination_dir / f"{source.stem}{self.suffix}.png"
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
        target = Path(destination)
        if target.suffix.lower() != ".png":
            target = target.with_suffix(".png")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ExportError(
                f"Não foi possível criar a pasta de destino:\n{target.parent}",
                detail=str(exc),
            ) from exc

        payload = image if image.mode == "RGBA" else image.convert("RGBA")

        try:
            payload.save(target, format="PNG", optimize=True)
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

    def export(self, image: Image.Image, source: Path, destination_dir: Path) -> Path:
        """Exporta a imagem para uma pasta, derivando o nome da origem.

        Args:
            image: Imagem processada.
            source: Caminho da imagem original (usado para nomear a saída).
            destination_dir: Pasta de destino.

        Returns:
            Caminho do arquivo gravado.

        Raises:
            ExportError: Se a gravação falhar.
        """
        return self.save_png(image, self.build_output_path(source, Path(destination_dir)))
