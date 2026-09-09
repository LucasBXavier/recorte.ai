"""Preferências persistentes do usuário (idioma, layout da janela).

Gravadas em :data:`config.PREFERENCES_PATH`, fora da pasta do aplicativo, já
que o executável do PyInstaller pode rodar de um diretório temporário
somente leitura. Qualquer falha de leitura ou escrita é silenciosa: as
preferências são um detalhe de conveniência, nunca algo que deveria impedir
o aplicativo de abrir ou funcionar.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from config import PREFERENCES_PATH, SIDEBAR_DEFAULT_WIDTH


@dataclass
class Preferences:
    """Preferências salvas entre execuções do aplicativo.

    Attributes:
        language: Código do idioma da interface (``"pt"`` ou ``"en"``).
        sidebar_width: Largura da barra lateral, em pixels.
    """

    language: str = "pt"
    sidebar_width: int = SIDEBAR_DEFAULT_WIDTH


def load_preferences() -> Preferences:
    """Carrega as preferências salvas, ou os valores padrão se não houver nada.

    Returns:
        Preferências carregadas do disco, ou :class:`Preferences` padrão se
        o arquivo não existir ou estiver corrompido.
    """
    try:
        raw = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Preferences()

    return Preferences(
        language=str(raw.get("language", "pt")),
        sidebar_width=int(raw.get("sidebar_width", SIDEBAR_DEFAULT_WIDTH)),
    )


def save_preferences(preferences: Preferences) -> None:
    """Grava as preferências em disco, ignorando falhas de escrita.

    Args:
        preferences: Preferências a salvar.
    """
    try:
        PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
        PREFERENCES_PATH.write_text(
            json.dumps(asdict(preferences), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
