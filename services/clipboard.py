"""Cópia de imagens para a área de transferência do Windows.

Grava dois formatos ao mesmo tempo:

- ``"PNG"`` bruto, que preserva o canal alfa em aplicativos que reconhecem o
  formato (navegadores, Photoshop, GIMP, Paint.NET, versões recentes do
  Office);
- ``CF_DIB`` opaco sobre fundo branco, para compatibilidade com aplicativos
  mais simples que só entendem bitmap comum (Paint clássico, WordPad).

Cada aplicativo de destino escolhe o formato que sabe interpretar ao colar.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from io import BytesIO

from PIL import Image

from services.errors import AppError

CF_DIB: int = 8
GMEM_MOVEABLE: int = 0x0002

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalLock.restype = wintypes.LPVOID
_kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.SetClipboardData.restype = wintypes.HANDLE
_user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
_user32.RegisterClipboardFormatW.restype = wintypes.UINT
_user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]


class ClipboardError(AppError):
    """Falha ao copiar a imagem para a área de transferência do Windows."""

    title = "Erro ao copiar"
    title_key = "error.clipboard_title"


def _alloc_global(payload: bytes) -> int:
    """Aloca memória global do Windows e copia os bytes informados.

    Args:
        payload: Dados a colocar na memória alocada.

    Returns:
        Handle (``HGLOBAL``) da memória alocada e preenchida.

    Raises:
        ClipboardError: Se a alocação ou a cópia falharem.
    """
    handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, ctypes.c_size_t(len(payload)))
    if not handle:
        raise ClipboardError(
            "Não foi possível alocar memória para copiar a imagem.",
            key="error.clipboard_alloc",
        )

    locked = _kernel32.GlobalLock(handle)
    if not locked:
        _kernel32.GlobalFree(handle)
        raise ClipboardError(
            "Não foi possível preparar os dados para a área de transferência.",
            key="error.clipboard_lock",
        )

    ctypes.memmove(locked, payload, len(payload))
    _kernel32.GlobalUnlock(handle)
    return handle


def _set_format(fmt: int, payload: bytes) -> bool:
    """Grava um formato de dado na área de transferência já aberta.

    Args:
        fmt: Identificador do formato (``CF_DIB`` ou um formato registrado).
        payload: Bytes a gravar.

    Returns:
        ``True`` se o Windows aceitou o formato, ``False`` caso contrário.
    """
    handle = _alloc_global(payload)
    if not _user32.SetClipboardData(fmt, handle):
        _kernel32.GlobalFree(handle)
        return False
    return True


def copy_image(image: Image.Image) -> None:
    """Copia uma imagem para a área de transferência do Windows.

    Args:
        image: Imagem (qualquer modo do Pillow) a copiar.

    Raises:
        ClipboardError: Se a área de transferência não puder ser aberta ou
            estiver sendo usada por outro programa.
    """
    rgba = image if image.mode == "RGBA" else image.convert("RGBA")

    png_buffer = BytesIO()
    rgba.save(png_buffer, format="PNG")
    png_bytes = png_buffer.getvalue()

    opaque = Image.new("RGB", rgba.size, "#FFFFFF")
    opaque.paste(rgba, mask=rgba.getchannel("A"))
    bmp_buffer = BytesIO()
    opaque.save(bmp_buffer, format="BMP")
    # Os primeiros 14 bytes são o BITMAPFILEHEADER, que o CF_DIB não usa.
    dib_bytes = bmp_buffer.getvalue()[14:]

    png_format = _user32.RegisterClipboardFormatW("PNG")

    if not _user32.OpenClipboard(None):
        raise ClipboardError(
            "Não foi possível abrir a área de transferência.\n"
            "Feche outros programas que possam estar usando-a e tente novamente.",
            key="error.clipboard_open",
        )
    try:
        _user32.EmptyClipboard()
        png_ok = _set_format(png_format, png_bytes)
        dib_ok = _set_format(CF_DIB, dib_bytes)
    finally:
        _user32.CloseClipboard()

    if not (png_ok or dib_ok):
        raise ClipboardError(
            "Não foi possível copiar a imagem para a área de transferência.",
            key="error.clipboard_copy_failed",
        )
