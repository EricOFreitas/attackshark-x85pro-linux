"""Testes do encoder de imagem (sem hardware)."""

from PIL import Image

from xshark import image
from xshark.protocol import FRAME_BYTES, SCREEN_HEIGHT, SCREEN_WIDTH


def test_encode_pixel_rgb565_big_endian():
    assert image._encode_pixel(255, 255, 255) == (0xFF, 0xFF)  # branco
    assert image._encode_pixel(0, 0, 0) == (0x00, 0x00)  # preto
    assert image._encode_pixel(255, 0, 0) == (0xF8, 0x00)  # vermelho puro
    assert image._encode_pixel(0, 255, 0) == (0x07, 0xE0)  # verde puro
    assert image._encode_pixel(0, 0, 255) == (0x00, 0x1F)  # azul puro


def test_encode_frame_is_column_major():
    # 2x2: pixel (0,0)=branco, resto preto -> primeiro par de bytes é 0xFFFF
    im = Image.new("RGB", (2, 2), (0, 0, 0))
    im.putpixel((0, 0), (255, 255, 255))
    out = image._encode_frame(im, 2, 2)
    assert len(out) == 2 * 2 * 2
    assert out[0:2] == b"\xff\xff"  # coluna 0, linha 0
    assert out[2:4] == b"\x00\x00"  # coluna 0, linha 1


def test_load_frames_static_image(tmp_path):
    path = tmp_path / "x.png"
    Image.new("RGB", (50, 50), (10, 20, 30)).save(path)
    frames, interval = image.load_frames(str(path))
    assert len(frames) == 1
    assert len(frames[0]) == FRAME_BYTES  # frame completo com padding
    assert isinstance(interval, int)


def test_load_frames_animated_gif(tmp_path):
    path = tmp_path / "a.gif"
    imgs = [Image.new("RGB", (40, 40), c) for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=80, loop=0)
    frames, interval = image.load_frames(str(path))
    assert len(frames) == 3
    assert all(len(f) == FRAME_BYTES for f in frames)
    assert 1 <= interval <= 255


def test_default_screen_dims_are_x85():
    assert (SCREEN_WIDTH, SCREEN_HEIGHT) == (138, 180)


def test_fit_mode_letterboxes_without_crashing(tmp_path):
    from xshark.protocol import VISIBLE_HEIGHT, SCREEN_HEIGHT

    assert VISIBLE_HEIGHT < SCREEN_HEIGHT  # parte do framebuffer é off-screen
    path = tmp_path / "wide.png"
    Image.new("RGB", (300, 100), (200, 50, 50)).save(path)  # imagem larga
    frames, _ = image.load_frames(str(path), fit=True)
    assert len(frames) == 1
    assert len(frames[0]) == FRAME_BYTES
