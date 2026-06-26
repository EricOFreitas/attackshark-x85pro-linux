"""Converte PNG/JPG/GIF no buffer da tela (RGB565 big-endian, column-major).

O framebuffer é maior que a área visível: a imagem é colocada na janela visível
(VISIBLE_W x VISIBLE_HEIGHT, alinhada ao topo) e o resto fica preto/off-screen.
Por padrão a imagem preenche a janela (pode esticar); com fit=True a proporção é
preservada (letterbox).
"""

from __future__ import annotations

from .protocol import (
    FRAME_BYTES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    VISIBLE_HEIGHT,
    VISIBLE_W,
    VISIBLE_X,
    VISIBLE_Y,
)


def _encode_pixel(r: int, g: int, b: int) -> tuple[int, int]:
    v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return (v >> 8) & 0xFF, v & 0xFF


def _encode_frame(img, width: int, height: int) -> bytes:
    """Codifica um PIL.Image RGB (width x height) em RGB565 BE column-major."""
    px = img.load()
    out = bytearray(width * height * 2)
    i = 0
    for x in range(width):
        for y in range(height):
            r, g, b = px[x, y][:3]
            out[i], out[i + 1] = _encode_pixel(r, g, b)
            i += 2
    return bytes(out)


def load_frames(
    path: str,
    width: int = SCREEN_WIDTH,
    height: int = SCREEN_HEIGHT,
    visible_x: int = VISIBLE_X,
    visible_w: int = VISIBLE_W,
    visible_y: int = VISIBLE_Y,
    visible_h: int = VISIBLE_HEIGHT,
    fit: bool = False,
) -> tuple[list[bytes], int]:
    """Retorna (lista de frames codificados, intervalo_ms médio).

    A imagem vai na janela visível (visible_w x visible_h). Com fit=True a proporção
    é preservada (letterbox); senão preenche a janela (pode esticar).
    Levanta RuntimeError se o Pillow não estiver instalado.
    """
    try:
        from PIL import Image, ImageOps, ImageSequence
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Falta o Pillow: pip install pillow") from exc

    img = Image.open(path)
    frames: list[bytes] = []
    durations: list[int] = []

    for frame in ImageSequence.Iterator(img):
        canvas = Image.new("RGB", (width, height), (0, 0, 0))
        src = frame.convert("RGB")
        if fit:
            # preserva proporção dentro da janela e centraliza
            fitted = ImageOps.contain(src, (visible_w, visible_h))
            ox = visible_x + (visible_w - fitted.width) // 2
            oy = visible_y + (visible_h - fitted.height) // 2
            canvas.paste(fitted, (ox, oy))
        else:
            canvas.paste(src.resize((visible_w, visible_h)), (visible_x, visible_y))
        # encoda em column-major e completa o slot de frame esperado pelo device
        encoded = _encode_frame(canvas, width, height).ljust(FRAME_BYTES, b"\x00")
        frames.append(encoded)
        durations.append(int(frame.info.get("duration", 100)))

    interval = min(255, max(1, sum(durations) // len(durations))) if durations else 100
    return frames, interval
