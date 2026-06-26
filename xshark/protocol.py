"""Montagem dos pacotes do canal vendor da tela.

O formato do frame foi reversado pelo projeto AttackManatee para o K86 (mesmo
vendor 0x3151, mesmo canal usagePage=0xFFFF/usage=0x0002, feature report de 64 bytes).
Confirmado compatível com o X85 Pro (3151:5002). Crédito:
https://github.com/Jinori/AttackManatee  (docs/protocol.md)

Frame de saída:
    [opcode][reservado...][checksum][payload opcional][zero-pad até 64 bytes]

Checksum (cobre só o header de 7 bytes, byte 0..6):
    (0xFF - (sum(header[0:7]) & 0xFF)) & 0xFF
"""

from __future__ import annotations

import datetime as _dt

REPORT_SIZE = 64

# Opcodes conhecidos (do protocolo do K86).
OP_FIRMWARE = 0x8F
OP_BRIGHTNESS = 0x07
OP_IMAGE_INIT = 0xA5
OP_IMAGE_CHUNK = 0x25
OP_SET_TIME = 0x28
OP_CLEAR = 0xAC


def _checksum(header7: bytes) -> int:
    """Checksum do header (7 bytes, posições 0..6)."""
    return (0xFF - (sum(header7) & 0xFF)) & 0xFF


def build_set_time(when: _dt.datetime | None = None) -> bytes:
    """Monta o pacote do comando 0x28 (set clock) com a hora dada (ou agora).

    Layout:
        byte 0     opcode 0x28
        byte 1-6   reservado (0x00)
        byte 7     checksum (0xD7 para este header)
        byte 8-9   ano  (uint16 big-endian)
        byte 10    mês (1-12)
        byte 11    dia (1-31)
        byte 12    hora (0-23)
        byte 13    minuto (0-59)
        byte 14    segundo (0-59)
    O resto é preenchido com zero (feito na camada de transporte).
    """
    when = when or _dt.datetime.now()
    header = bytes([OP_SET_TIME, 0, 0, 0, 0, 0, 0])
    payload = header + bytes([_checksum(header)]) + bytes(
        [
            (when.year >> 8) & 0xFF,
            when.year & 0xFF,
            when.month,
            when.day,
            when.hour,
            when.minute,
            when.second,
        ]
    )
    return payload


def build_clear() -> bytes:
    """Comando 0xAC (limpar tela)."""
    header = bytes([OP_CLEAR, 0, 0, 0, 0, 0, 0])
    return header + bytes([_checksum(header)])


# --- Imagem / GIF (opcodes 0xA5 init e 0x25 chunk) -------------------------
#
# Buffer da tela do X85 Pro (decifrado por calibração visual; ajustável por CLI):
#   180 x 179, RGB565 big-endian, ordem column-major. A tela inteira é visível.
#   O "slot" de frame que o firmware espera é de 64800 bytes (180x179 = 64440
#   bytes de pixel + padding até 64800). (O K86 é 240x135 — modelos diferem.)
SCREEN_WIDTH = 180
SCREEN_HEIGHT = 179
VISIBLE_X = 0
VISIBLE_W = 180
FRAME_BYTES = 64800  # tamanho do slot de 1 frame esperado pelo dispositivo

CHUNK_DATA_LEN = 56  # 0x38 bytes de pixel por chunk (o último frame pode ter menos)


def build_image_init(
    frame_count: int,
    interval_ms: int,
    size_per_frame: int = FRAME_BYTES,
    x_offset: int = 0,
    width: int = SCREEN_WIDTH,
    height: int = SCREEN_HEIGHT,
) -> bytes:
    """Comando 0xA5: prepara o envio de 1 imagem (frame_count=1) ou animação.

        A5 00 <nframes> <interval> <size_lo> <size_hi> 00 <csum> | <x_lo> <x_hi> <w> <h>

    `size_per_frame` é o tamanho em bytes de um frame (uint16 little-endian).
    Os 4 bytes finais (trailing) NÃO entram no checksum.
    """
    header = bytes(
        [
            OP_IMAGE_INIT,
            0x00,
            frame_count & 0xFF,
            interval_ms & 0xFF,
            size_per_frame & 0xFF,
            (size_per_frame >> 8) & 0xFF,
            0x00,
        ]
    )
    trailing = bytes([x_offset & 0xFF, (x_offset >> 8) & 0xFF, width & 0xFF, height & 0xFF])
    return header + bytes([_checksum(header)]) + trailing


def chunkify(frame: bytes, chunk_len: int = CHUNK_DATA_LEN):
    """Quebra os bytes de um frame em (chunk_idx, data) sequenciais."""
    for idx, base in enumerate(range(0, len(frame), chunk_len)):
        yield idx, frame[base : base + chunk_len]


def build_image_chunk(
    frame_idx: int,
    frame_count: int,
    interval_ms: int,
    chunk_idx: int,
    data: bytes,
) -> bytes:
    """Comando 0x25: um pedaço de pixels.

        25 <frame_idx> <nframes> <interval> <chunk_lo> <chunk_hi> <data_len> <csum> | <data...>

    `chunk_idx` é uint16 little-endian. Os pixels (data) NÃO entram no checksum.
    """
    header = bytes(
        [
            OP_IMAGE_CHUNK,
            frame_idx & 0xFF,
            frame_count & 0xFF,
            interval_ms & 0xFF,
            chunk_idx & 0xFF,
            (chunk_idx >> 8) & 0xFF,
            len(data) & 0xFF,
        ]
    )
    return header + bytes([_checksum(header)]) + data
