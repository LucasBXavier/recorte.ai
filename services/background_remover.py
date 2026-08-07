"""Serviço de remoção de fundo baseado no ``rembg``.

O modelo é carregado de forma preguiçosa (lazy) e reaproveitado entre
execuções, o que torna a primeira imagem mais lenta e todas as seguintes
praticamente instantâneas.
"""

from __future__ import annotations

import threading
from typing import Any

from PIL import Image

from config import FALLBACK_MODEL, PRIMARY_MODEL
from services.errors import ModelError


class BackgroundRemover:
    """Encapsula o modelo de IA responsável por separar objeto e fundo.

    Attributes:
        primary_model: Nome do modelo preferencial.
        fallback_model: Modelo usado caso o preferencial não possa ser carregado.
    """

    def __init__(
        self,
        primary_model: str = PRIMARY_MODEL,
        fallback_model: str = FALLBACK_MODEL,
    ) -> None:
        """Inicializa o serviço sem carregar nenhum modelo ainda.

        Args:
            primary_model: Nome do modelo principal do ``rembg``.
            fallback_model: Nome do modelo alternativo.
        """
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self._session: Any | None = None
        self._active_model: str = ""
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Propriedades
    # ------------------------------------------------------------------ #

    @property
    def active_model(self) -> str:
        """Nome do modelo atualmente carregado (vazio se ainda não carregado)."""
        return self._active_model

    @property
    def is_ready(self) -> bool:
        """Indica se o modelo já está carregado em memória."""
        return self._session is not None

    # ------------------------------------------------------------------ #
    # Carregamento
    # ------------------------------------------------------------------ #

    def warm_up(self) -> str:
        """Força o carregamento do modelo.

        Útil para adiantar o download/inicialização em segundo plano assim que
        o aplicativo abre.

        Returns:
            O nome do modelo carregado.

        Raises:
            ModelError: Se nenhum dos modelos puder ser inicializado.
        """
        self._ensure_session()
        return self._active_model

    def _ensure_session(self) -> Any:
        """Garante que exista uma sessão do ``rembg`` pronta para uso.

        Returns:
            A sessão ativa do ``rembg``.

        Raises:
            ModelError: Se o ``rembg`` não estiver instalado ou nenhum modelo
                puder ser carregado.
        """
        if self._session is not None:
            return self._session

        with self._lock:
            if self._session is not None:
                return self._session

            try:
                from rembg import new_session
            except ImportError as exc:  # pragma: no cover - ambiente sem rembg
                raise ModelError(
                    "A biblioteca de IA (rembg) não está instalada.\n"
                    "Execute: pip install -r requirements.txt",
                    detail=str(exc),
                ) from exc

            errors: list[str] = []
            for model_name in (self.primary_model, self.fallback_model):
                if not model_name:
                    continue
                try:
                    self._session = new_session(model_name)
                    self._active_model = model_name
                    return self._session
                except Exception as exc:  # noqa: BLE001 - fallback intencional
                    errors.append(f"{model_name}: {exc}")

            raise ModelError(
                "Não foi possível carregar o modelo de IA.\n"
                "Verifique sua conexão na primeira execução — o modelo é "
                "baixado uma única vez.",
                detail=" | ".join(errors),
            )

    # ------------------------------------------------------------------ #
    # Processamento
    # ------------------------------------------------------------------ #

    def remove(self, image: Image.Image) -> Image.Image:
        """Remove o fundo de uma imagem.

        Args:
            image: Imagem de entrada em qualquer modo do Pillow.

        Returns:
            Nova imagem em modo ``RGBA`` com o fundo transparente.

        Raises:
            ModelError: Se a inferência falhar.
        """
        session = self._ensure_session()

        try:
            from rembg import remove as rembg_remove
        except ImportError as exc:  # pragma: no cover - ambiente sem rembg
            raise ModelError(
                "A biblioteca de IA (rembg) não está instalada.",
                detail=str(exc),
            ) from exc

        source = image if image.mode == "RGBA" else image.convert("RGBA")

        try:
            result = rembg_remove(source, session=session, post_process_mask=True)
        except Exception as exc:  # noqa: BLE001 - erro do runtime da IA
            raise ModelError(
                "O modelo de IA não conseguiu processar esta imagem.\n"
                "Tente novamente ou use outra imagem.",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

        if not isinstance(result, Image.Image):  # pragma: no cover - defensivo
            raise ModelError(
                "O modelo de IA devolveu um resultado inesperado.",
                detail=f"tipo={type(result)!r}",
            )

        return result if result.mode == "RGBA" else result.convert("RGBA")

    def release(self) -> None:
        """Libera a sessão do modelo da memória."""
        with self._lock:
            self._session = None
            self._active_model = ""
