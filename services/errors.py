"""Exceções de domínio da aplicação.

Todas herdam de :class:`AppError`, o que permite à interface capturar um único
tipo e exibir sempre uma mensagem amigável ao usuário.
"""

from __future__ import annotations


class AppError(Exception):
    """Erro previsto pela aplicação, com mensagem pronta para o usuário."""

    #: Título curto exibido no diálogo de erro.
    title: str = "Ops, algo deu errado"

    def __init__(self, message: str, *, detail: str = "") -> None:
        """Inicializa o erro.

        Args:
            message: Texto amigável explicando o que aconteceu.
            detail: Informação técnica opcional (exceção original, caminho...).
        """
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - representação simples
        return self.message


class InvalidImageError(AppError):
    """A imagem tem formato não suportado ou não pôde ser lida."""

    title = "Imagem inválida"


class CorruptedFileError(AppError):
    """O arquivo existe, mas está corrompido ou incompleto."""

    title = "Arquivo corrompido"


class ModelError(AppError):
    """Falha ao carregar ou executar o modelo de inteligência artificial."""

    title = "Erro no modelo de IA"


class ExportError(AppError):
    """Falha ao gravar o arquivo de saída em disco."""

    title = "Erro ao salvar"
