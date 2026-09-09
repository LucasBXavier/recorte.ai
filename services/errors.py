"""Exceções de domínio da aplicação.

Todas herdam de :class:`AppError`, o que permite à interface capturar um único
tipo e exibir sempre uma mensagem amigável ao usuário.
"""

from __future__ import annotations


class AppError(Exception):
    """Erro previsto pela aplicação, com mensagem pronta para o usuário.

    ``message``/``title`` continuam em português puro (para quem usa os
    serviços diretamente em script, sem a interface, veja o README). Já
    ``key``/``params`` e ``title_key`` são opcionais e permitem à interface
    traduzir o erro via :func:`i18n.t` quando presentes, sem que os serviços
    precisem importar nada de UI.
    """

    #: Título curto exibido no diálogo de erro (fallback em português).
    title: str = "Ops, algo deu errado"
    #: Chave de tradução do título, usada pela interface quando disponível.
    title_key: str = "error.generic_title"

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        key: str = "",
        params: dict[str, object] | None = None,
    ) -> None:
        """Inicializa o erro.

        Args:
            message: Texto amigável explicando o que aconteceu (português).
            detail: Informação técnica opcional (exceção original, caminho...).
            key: Chave de tradução em :mod:`i18n`, para a interface exibir a
                mensagem no idioma ativo. Vazia quando não há tradução.
            params: Valores para interpolar na mensagem traduzida.
        """
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.key = key
        self.params = params or {}

    def __str__(self) -> str:  # pragma: no cover - representação simples
        return self.message


class InvalidImageError(AppError):
    """A imagem tem formato não suportado ou não pôde ser lida."""

    title = "Imagem inválida"
    title_key = "error.invalid_image_title"


class CorruptedFileError(AppError):
    """O arquivo existe, mas está corrompido ou incompleto."""

    title = "Arquivo corrompido"
    title_key = "error.corrupted_file_title"


class ModelError(AppError):
    """Falha ao carregar ou executar o modelo de inteligência artificial."""

    title = "Erro no modelo de IA"
    title_key = "error.model_title"


class ExportError(AppError):
    """Falha ao gravar o arquivo de saída em disco."""

    title = "Erro ao salvar"
    title_key = "error.export_title"
