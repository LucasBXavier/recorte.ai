"""Gera ``icon.ico`` e ``logo.png`` do aplicativo.

Executar apenas quando quiser recriar os assets::

    python assets/generate_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).resolve().parent

PRIMARY = (59, 130, 246, 255)
PRIMARY_DEEP = (37, 99, 235, 255)
WHITE = (255, 255, 255, 255)
CHECKER_A = (255, 255, 255, 70)
CHECKER_B = (255, 255, 255, 22)


def _vertical_gradient(size: int, top: tuple[int, ...], bottom: tuple[int, ...]) -> Image.Image:
    """Cria um degradê vertical entre duas cores.

    Args:
        size: Lado do quadrado, em pixels.
        top: Cor RGBA do topo.
        bottom: Cor RGBA da base.

    Returns:
        Imagem quadrada com o degradê.
    """
    gradient = Image.new("RGBA", (1, size))
    for y in range(size):
        ratio = y / max(1, size - 1)
        gradient.putpixel(
            (0, y),
            tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(4)),  # type: ignore[arg-type]
        )
    return gradient.resize((size, size))


def build_logo(size: int = 512) -> Image.Image:
    """Desenha o logotipo do aplicativo.

    O símbolo combina um recorte em silhueta (o objeto preservado) com o padrão
    xadrez que representa a transparência do fundo removido.

    Args:
        size: Lado da imagem quadrada gerada.

    Returns:
        Imagem ``RGBA`` do logotipo.
    """
    scale = 4
    canvas = size * scale
    unit = canvas / 512

    mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, canvas - 1, canvas - 1), radius=int(112 * unit), fill=255
    )

    base = _vertical_gradient(canvas, PRIMARY, PRIMARY_DEEP)

    # Metade direita com xadrez de transparência.
    checker = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    checker_draw = ImageDraw.Draw(checker)
    tile = int(48 * unit)
    for y in range(0, canvas, tile):
        for x in range(int(canvas / 2), canvas, tile):
            color = CHECKER_A if ((x // tile) + (y // tile)) % 2 == 0 else CHECKER_B
            checker_draw.rectangle((x, y, x + tile, y + tile), fill=color)
    base.alpha_composite(checker)

    # Silhueta central preservada.
    draw = ImageDraw.Draw(base)
    head_r = int(72 * unit)
    center_x = canvas // 2
    draw.ellipse(
        (center_x - head_r, int(112 * unit), center_x + head_r, int(112 * unit) + head_r * 2),
        fill=WHITE,
    )
    draw.ellipse(
        (int(118 * unit), int(286 * unit), int(394 * unit), int(534 * unit)), fill=WHITE
    )
    draw.rectangle(
        (int(118 * unit), int(410 * unit), int(394 * unit), canvas), fill=WHITE
    )

    base.putalpha(mask)
    return base.resize((size, size), Image.LANCZOS)


def main() -> None:
    """Gera e grava os arquivos de logo e ícone."""
    logo = build_logo(512)
    logo.save(ASSETS_DIR / "logo.png", format="PNG", optimize=True)
    logo.save(
        ASSETS_DIR / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Assets gerados em {ASSETS_DIR}")


if __name__ == "__main__":
    main()
