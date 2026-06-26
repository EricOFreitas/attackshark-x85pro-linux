"""Testes das funções puras de montagem de pacotes (sem hardware)."""

import datetime

import pytest

from xshark import protocol as p


def test_checksum_formula():
    assert p._checksum(bytes([0x28, 0, 0, 0, 0, 0, 0])) == 0xD7
    assert p._checksum(bytes(7)) == 0xFF


def test_set_time_matches_reference_vector():
    # Vetor de referência do AttackManatee: 2026-05-14 18:55:21
    pkt = p.build_set_time(datetime.datetime(2026, 5, 14, 18, 55, 21))
    assert pkt.hex(" ") == "28 00 00 00 00 00 00 d7 07 ea 05 0e 12 37 15"


def test_set_time_year_big_endian():
    pkt = p.build_set_time(datetime.datetime(2024, 1, 1, 0, 0, 0))
    assert pkt[8:10] == bytes([0x07, 0xE8])  # 2024 = 0x07E8


def test_clear_packet():
    pkt = p.build_clear()
    assert pkt[0] == p.OP_CLEAR
    assert pkt[7] == p._checksum(pkt[:7])


def test_image_init_layout():
    pkt = p.build_image_init(frame_count=1, interval_ms=100, size_per_frame=64800)
    assert pkt[0] == p.OP_IMAGE_INIT
    assert pkt[2] == 1  # frame_count
    assert pkt[3] == 100  # interval
    assert pkt[4:6] == bytes([0x20, 0xFD])  # 64800 little-endian
    assert pkt[7] == p._checksum(pkt[:7])  # checksum
    assert len(pkt) == 12  # 8 header + 4 trailing
    assert pkt[10] == p.SCREEN_WIDTH and pkt[11] == p.SCREEN_HEIGHT


def test_image_init_rejects_bad_args():
    with pytest.raises(ValueError):
        p.build_image_init(1, 100, size_per_frame=70000)
    with pytest.raises(ValueError):
        p.build_image_init(frame_count=300, interval_ms=100)


def test_image_chunk_layout_and_checksum():
    data = bytes(range(56))
    pkt = p.build_image_chunk(0, 1, 100, chunk_idx=0, data=data)
    assert pkt[0] == p.OP_IMAGE_CHUNK
    assert pkt[6] == 56  # data_len
    assert pkt[7] == p._checksum(pkt[:7])
    assert pkt[8:] == data
    assert len(pkt) == 64


def test_chunk_idx_little_endian():
    pkt = p.build_image_chunk(0, 1, 100, chunk_idx=0x0102, data=b"\x00")
    assert pkt[4] == 0x02 and pkt[5] == 0x01


def test_chunkify_counts_full_frame():
    # 64800 bytes => 1157 chunks de 56 + 1 de 8 = 1158
    chunks = list(p.chunkify(bytes(p.FRAME_BYTES)))
    assert len(chunks) == 1158
    assert all(idx == i for i, (idx, _) in enumerate(chunks))
    assert len(chunks[-1][1]) == 8
    assert sum(len(d) for _, d in chunks) == p.FRAME_BYTES
