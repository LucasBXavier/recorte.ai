"""Orquestração do fluxo completo: carregar, remover fundo, ajustar e salvar.

Concentrar o fluxo aqui evita duplicação entre o modo de imagem única e o
processamento em lote, e mantém a interface livre de regras de negócio.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from pathlib import Path

from PIL import Image

from config import BatchReport, JobResult, ProcessingOptions
from services.background_remover import BackgroundRemover
from services.errors import AppError
from services.export_service import ExportService
from services.image_processor import ImageProcessor

#: Assinatura do callback de progresso: ``(atual, total, nome_do_arquivo)``.
ProgressCallback = Callable[[int, int, str], None]

#: Recorte bruto da IA, antes do pós-processamento: ``(recorte, tamanho
#: original, imagem original)``. Guardar isso permite à interface reaplicar
#: ajustes (suavização, fundo, redimensionamento) sem rodar o modelo de novo.
RawCutout = tuple[Image.Image, tuple[int, int], Image.Image]

#: Assinatura do callback de item concluído: ``(índice, total, resultado,
#: imagem, recorte_bruto)``. ``índice`` é baseado em zero; ``imagem`` e
#: ``recorte_bruto`` são ``None`` quando o item falhou.
ItemCallback = Callable[[int, int, JobResult, "Image.Image | None", "RawCutout | None"], None]


class RemovalPipeline:
    """Executa a remoção de fundo de uma ou várias imagens."""

    def __init__(
        self,
        remover: BackgroundRemover | None = None,
        exporter: ExportService | None = None,
    ) -> None:
        """Inicializa o pipeline.

        Args:
            remover: Serviço de IA. Um novo é criado se omitido.
            exporter: Serviço de exportação. Um novo é criado se omitido.
        """
        self.remover = remover or BackgroundRemover()
        self.exporter = exporter or ExportService()
        self._cancel_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Controle
    # ------------------------------------------------------------------ #

    def request_cancel(self) -> None:
        """Sinaliza que o lote em andamento deve parar na próxima imagem."""
        self._cancel_event.set()

    def reset_cancel(self) -> None:
        """Limpa o sinal de cancelamento antes de iniciar um novo trabalho."""
        self._cancel_event.clear()

    @property
    def cancelled(self) -> bool:
        """Indica se um cancelamento foi solicitado."""
        return self._cancel_event.is_set()

    # ------------------------------------------------------------------ #
    # Execução
    # ------------------------------------------------------------------ #

    def remove_background_only(self, path: Path) -> RawCutout:
        """Executa somente a remoção de fundo, a etapa cara do processamento.

        Separar essa etapa do pós-processamento permite reaplicar ajustes
        (suavização, fundo, redimensionamento) instantaneamente, sem rodar o
        modelo de IA de novo a cada mudança de opção.

        Args:
            path: Caminho da imagem de origem.

        Returns:
            Tupla ``(recorte bruto, tamanho original, imagem original)``.

        Raises:
            AppError: Em qualquer falha prevista (leitura ou IA).
        """
        source = ImageProcessor.load(path)
        original_size = source.size
        cutout = self.remover.remove(source)
        return cutout, original_size, source

    def process_image(self, path: Path, options: ProcessingOptions) -> Image.Image:
        """Processa uma imagem e devolve o resultado em memória.

        Args:
            path: Caminho da imagem de origem.
            options: Opções de pós-processamento.

        Returns:
            Imagem ``RGBA`` com o fundo removido e os ajustes aplicados.

        Raises:
            AppError: Em qualquer falha prevista (leitura, IA ou ajuste).
        """
        cutout, original_size, source = self.remove_background_only(path)
        return ImageProcessor.apply_options(cutout, options, original_size, source)

    def process_batch(
        self,
        paths: Iterable[Path],
        destination_dir: Path,
        options: ProcessingOptions,
        on_progress: ProgressCallback | None = None,
        on_item: ItemCallback | None = None,
    ) -> BatchReport:
        """Processa e salva várias imagens em sequência.

        Erros individuais não interrompem o lote: cada falha é registrada no
        relatório e o processamento continua.

        Args:
            paths: Caminhos das imagens a processar.
            destination_dir: Pasta onde os PNGs serão gravados.
            options: Opções de pós-processamento.
            on_progress: Callback chamado antes de cada imagem, recebendo
                ``(índice, total, nome_do_arquivo)``.
            on_item: Callback chamado logo após cada imagem ser processada
                (com sucesso ou não), recebendo ``(índice, total, resultado,
                imagem, recorte_bruto)``. Permite à interface exibir o
                resultado assim que fica pronto, mesmo em lote, e reaplicar
                ajustes depois sem rodar a IA de novo. ``recorte_bruto`` vem
                preenchido sempre que a remoção de fundo em si deu certo,
                mesmo que a exportação para disco tenha falhado depois.

        Returns:
            Relatório com sucessos e falhas.
        """
        items = [Path(item) for item in paths]
        total = len(items)
        report = BatchReport()
        self.reset_cancel()

        for index, source in enumerate(items, start=1):
            if self.cancelled:
                break

            if on_progress is not None:
                on_progress(index, total, source.name)

            image: Image.Image | None = None
            raw: RawCutout | None = None
            try:
                cutout, original_size, original = self.remove_background_only(source)
                raw = (cutout, original_size, original)
                image = ImageProcessor.apply_options(cutout, options, original_size, original)
                output = self.exporter.export(
                    image, source, Path(destination_dir),
                    format=options.export_format, quality=options.export_quality,
                )
                result = JobResult(source=source, output=output)
            except AppError as exc:
                result = JobResult(source=source, success=False, message=exc.message)
            except Exception as exc:  # noqa: BLE001 - rede de segurança do lote
                result = JobResult(
                    source=source,
                    success=False,
                    message=f"Erro inesperado: {type(exc).__name__}",
                )

            report.results.append(result)
            if on_item is not None:
                # ``raw`` é repassado independente de ``result.success``: se a
                # etapa cara (IA) deu certo mas só a exportação falhou, ainda
                # vale a pena guardar o recorte para reaproveitar depois.
                on_item(index, total, result, image if result.success else None, raw)

        return report
