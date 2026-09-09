"""Verificação de novas versões via GitHub Releases.

Faz uma única chamada HTTP à API pública do GitHub ao abrir o aplicativo,
sem autenticação — o que só funciona se o repositório em :data:`config.UPDATE_REPO`
(ou ao menos seus Releases) for público. Qualquer falha na checagem é
silenciosa: sem internet, repositório ainda sem nenhum release publicado,
ou limite de requisições da API atingido são todos tratados da mesma forma,
já que checar atualização é um extra de conveniência, nunca algo que deveria
atrapalhar a abertura do aplicativo.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from config import APP_VERSION, UPDATE_REPO

_API_URL = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
_TIMEOUT_SECONDS = 4.0


@dataclass
class UpdateInfo:
    """Informação sobre uma versão mais nova disponível.

    Attributes:
        version: Número da versão, sem o prefixo "v" (ex.: ``"1.1.0"``).
        url: Endereço da página do Release no GitHub.
    """

    version: str
    url: str


def _parse_version(text: str) -> tuple[int, ...]:
    """Converte um texto de versão em uma tupla comparável.

    Args:
        text: Texto da versão, com ou sem o prefixo "v" (ex.: ``"v1.2.0"``).

    Returns:
        Tupla de inteiros para comparação (ex.: ``(1, 2, 0)``). Trechos sem
        dígitos viram ``0`` em vez de falhar, para tolerar sufixos como
        ``"1.2.0-beta"``.
    """
    cleaned = text.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in cleaned.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def check_for_update(current_version: str = APP_VERSION) -> UpdateInfo | None:
    """Consulta o Release mais recente do repositório e compara com a versão atual.

    Args:
        current_version: Versão instalada, usada na comparação.

    Returns:
        :class:`UpdateInfo` se houver uma versão mais nova publicada, ou
        ``None`` se a versão atual já é a mais recente, ou se a checagem
        falhar por qualquer motivo.
    """
    request = urllib.request.Request(
        _API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            # A API do GitHub recusa requisições sem User-Agent.
            "User-Agent": "Recorte.ai-update-checker",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - checagem é best-effort
        return None

    latest_tag = payload.get("tag_name")
    release_url = payload.get("html_url")
    if not latest_tag or not release_url:
        return None

    if _parse_version(latest_tag) <= _parse_version(current_version):
        return None

    return UpdateInfo(version=latest_tag.lstrip("vV"), url=release_url)
