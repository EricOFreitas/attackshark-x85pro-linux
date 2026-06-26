"""Acesso de baixo nível ao canal vendor (tela) do Attack Shark X85 Pro.

O canal de controle da tela é a interface HID com usage page 0xFFFF, que troca
Feature reports de 64 bytes (report id 0). Ver docs/PROTOCOL.md.
"""

from __future__ import annotations

VENDOR_ID = 0x3151
PRODUCT_ID = 0x5002

# Usage page vendor observada no report descriptor (06 ff ff).
VENDOR_USAGE_PAGE = 0xFFFF

# Tamanho do payload do feature report (Report Count = 0x40).
REPORT_SIZE = 64


def _hid():
    """Importa o binding hidapi com mensagem amigável se a lib C faltar."""
    try:
        import hid
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta a lib do hidapi. No Ubuntu: sudo apt install libhidapi-hidraw0"
        ) from exc
    return hid


def find_vendor_path() -> bytes:
    """Retorna o `path` hidraw da interface vendor (a que controla a tela).

    Há mais de uma interface com usage page 0xFFFF; o canal da tela é o que expõe
    o Feature report de 64 bytes (usage 0x0002, maior interface_number — ver
    docs/PROTOCOL.md). Levanta RuntimeError se o teclado não for encontrado.
    """
    candidates = _hid().enumerate(VENDOR_ID, PRODUCT_ID)
    if not candidates:
        raise RuntimeError(
            f"Teclado {VENDOR_ID:04x}:{PRODUCT_ID:04x} não encontrado. "
            "Está conectado por cabo USB?"
        )

    vendor = [c for c in candidates if c.get("usage_page", 0) >= 0xFF00]
    if vendor:
        # Entre os canais vendor, o da tela é o de maior interface_number
        # (iface 2 / usage 0x0002), confirmado pelo report descriptor de 64 bytes.
        return max(vendor, key=lambda i: i.get("interface_number", 0))["path"]

    # Fallback: maior interface_number costuma ser o canal vendor.
    return max(candidates, key=lambda i: i.get("interface_number", 0))["path"]


class XSharkDevice:
    """Abre o canal vendor e expõe feature reports crus.

    Use como context manager:

        with XSharkDevice() as dev:
            dev.send_feature(b"\\x01...")
    """

    def __init__(self, path: bytes | None = None):
        self._path = path or find_vendor_path()
        self._dev = None

    def __enter__(self) -> XSharkDevice:
        self._dev = _hid().Device(path=self._path)
        return self

    def __exit__(self, *exc) -> None:
        if self._dev is not None:
            self._dev.close()
            self._dev = None

    def _require(self):
        if self._dev is None:
            raise RuntimeError("Dispositivo não aberto (use 'with XSharkDevice() as dev').")
        return self._dev

    def send_feature(self, payload: bytes) -> int:
        """Envia um feature report. Faz pad/truncate para REPORT_SIZE.

        O primeiro byte enviado ao hidapi é o report id (0 aqui).
        """
        data = bytes(payload[:REPORT_SIZE]).ljust(REPORT_SIZE, b"\x00")
        return self._require().send_feature_report(b"\x00" + data)

    def get_feature(self, length: int = REPORT_SIZE) -> bytes:
        """Lê um feature report (report id 0)."""
        return bytes(self._require().get_feature_report(0, length + 1))
