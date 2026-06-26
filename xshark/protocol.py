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
