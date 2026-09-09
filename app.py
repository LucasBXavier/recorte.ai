"""Ponto de entrada do Recorte.ai.

Executar::

    python app.py

Gerar o executável::

    pyinstaller --onefile --windowed app.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from tkinter import messagebox
from types import TracebackType
from typing import Any

import customtkinter as ctk

from config import (
    APP_NAME,
    ICON_PATH,
    THEME,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from ui.main_window import MainWindow


def _build_root() -> ctk.CTk:
    """Cria a janela raiz, com suporte a arrastar e soltar quando disponível.

    O ``tkinterdnd2`` precisa injetar seu wrapper na raiz do Tk. Quando a
    biblioteca não está instalada, o aplicativo continua funcionando
    normalmente, apenas sem arrastar e soltar.

    Returns:
        A janela raiz configurada.
    """
    try:
        from tkinterdnd2 import TkinterDnD

        class DnDRoot(ctk.CTk, TkinterDnD.DnDWrapper):
            """Janela do CustomTkinter com suporte a arrastar e soltar."""

            def __init__(self) -> None:
                """Inicializa a raiz e registra o wrapper do tkinterdnd2."""
                super().__init__()
                self.TkdndVersion = TkinterDnD._require(self)

        return DnDRoot()
    except Exception:  # noqa: BLE001 - recurso opcional
        return ctk.CTk()


def _apply_icon(root: ctk.CTk) -> None:
    """Aplica o ícone da janela, ignorando falhas em sistemas não Windows.

    Args:
        root: Janela raiz.
    """
    icon = Path(ICON_PATH)
    if not icon.exists():
        return
    try:
        root.iconbitmap(str(icon))
    except Exception:  # noqa: BLE001 - ícone é opcional
        pass


def _install_exception_hook(root: ctk.CTk) -> None:
    """Garante que nenhuma exceção não tratada feche o aplicativo.

    Args:
        root: Janela raiz, usada para capturar erros de callbacks do Tk.
    """

    def show(kind: type[BaseException], value: BaseException,
             tb: TracebackType | None) -> None:
        """Exibe o erro em um diálogo e registra o traceback no console."""
        traceback.print_exception(kind, value, tb)
        try:
            messagebox.showerror(
                "Ops, algo deu errado",
                "Ocorreu um erro inesperado, mas o aplicativo continua aberto.\n\n"
                f"{kind.__name__}: {value}",
            )
        except Exception:  # noqa: BLE001 - não há mais o que fazer
            pass

    sys.excepthook = show

    def tk_report(_self: Any, *args: Any) -> None:
        """Redireciona erros de callbacks do Tkinter para o mesmo diálogo."""
        show(*sys.exc_info())  # type: ignore[arg-type]

    type(root).report_callback_exception = tk_report  # type: ignore[assignment]


def main() -> int:
    """Configura e executa o loop principal da interface.

    Returns:
        Código de saída do processo.
    """
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = _build_root()
    root.title(APP_NAME)
    root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
    root.minsize(*WINDOW_MIN_SIZE)
    root.configure(fg_color=THEME.background)

    _apply_icon(root)
    _install_exception_hook(root)

    window = MainWindow(root)
    window.pack(fill="both", expand=True)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
