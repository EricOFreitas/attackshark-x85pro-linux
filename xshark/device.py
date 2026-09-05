"""Acesso de baixo nível ao canal vendor (tela) do Attack Shark X85 Pro.

O canal de controle da tela é a interface HID com usage page 0xFFFF, que troca
Feature reports de 64 bytes (report id 0). Ver docs/PROTOCOL.md.
"""

from __future__ import annotations

import os

VENDOR_ID = 0x3151

# O teclado enumera com PIDs diferentes conforme o modo de conexão:
#   X85 Pro:  0x5002 — cabo USB   |  0x5006 — receptor 2.4G (dongle)
#   K86:      0x4015 — cabo USB   |  0x4011 — receptor 2.4G (dongle)
# O canal vendor da tela existe nos dois modos, com o mesmo protocolo.
# Bluetooth não expõe o canal vendor: use cabo ou dongle.
PRODUCT_IDS = (0x5002, 0x5006, 0x4015, 0x4011)

# Rótulo de modelo/modo por PID, usado pelo `probe`.
PRODUCT_NAMES = {
    0x5002: ("X85 Pro", "cabo USB"),
    0x5006: ("X85 Pro", "receptor 2.4G"),
    0x4015: ("K86", "cabo USB"),
    0x4011: ("K86", "receptor 2.4G"),
}

# Mantido por compatibilidade com quem importava o PID único.
PRODUCT_ID = PRODUCT_IDS[0]

# Usage page vendor observada no report descriptor (06 ff ff).
VENDOR_USAGE_PAGE = 0xFFFF

# Tamanho do payload do feature report (Report Count = 0x40).
REPORT_SIZE = 64


def product_ids() -> tuple[int, ...]:
    """PIDs a procurar, com override por ambiente para modelos não mapeados.

    XSHARK_PRODUCT_IDS aceita uma lista separada por vírgula, em hex ou decimal:
        XSHARK_PRODUCT_IDS=0x5006 xshark probe
    """
    raw = os.environ.get("XSHARK_PRODUCT_IDS", "").strip()
    if not raw:
        return PRODUCT_IDS
    ids = tuple(int(part, 0) for part in raw.split(",") if part.strip())
    return ids or PRODUCT_IDS


def _hid():
    """Importa o binding hidapi com mensagem amigável se a lib C faltar."""
    try:
        import hid
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta a lib do hidapi.\n"
            "  Arch/Omarchy:   sudo pacman -S hidapi python-hidapi\n"
            "  Debian/Ubuntu:  sudo apt install libhidapi-hidraw0 && pip install hid"
        ) from exc
    return hid


def _open_path(path: bytes):
    """Abre o canal vendor cobrindo os dois bindings Python do hidapi.

    Os dois se chamam `hid` mas têm APIs de abertura diferentes:
      * pyhidapi (PyPI `hid`, apmorton)          -> hid.Device(path=...)
      * cython-hidapi (Arch `python-hidapi`)     -> hid.device() + .open_path(...)
    Depois de abertos, ambos expõem send_feature_report/get_feature_report/close
    com a mesma assinatura, então o resto da classe não precisa saber qual é.
    """
    hid = _hid()
    if hasattr(hid, "Device"):
        return hid.Device(path=path)
    if hasattr(hid, "device"):
        dev = hid.device()
        dev.open_path(path)
        return dev
    raise RuntimeError(
        "O módulo 'hid' importado não é um binding hidapi reconhecido "
        f"(nem Device nem device em {getattr(hid, '__file__', '?')})."
    )


def enumerate_interfaces() -> list[dict]:
    """Lista as interfaces HID do teclado, em qualquer um dos PIDs conhecidos."""
    hid = _hid()
    found: list[dict] = []
    for pid in product_ids():
        found.extend(hid.enumerate(VENDOR_ID, pid))
    return found


def find_vendor_path() -> bytes:
    """Retorna o `path` hidraw da interface vendor (a que controla a tela).

    Há mais de uma interface com usage page 0xFFFF; o canal da tela é o que expõe
    o Feature report de 64 bytes (usage 0x0002, maior interface_number — ver
    docs/PROTOCOL.md). Levanta RuntimeError se o teclado não for encontrado.
    """
    candidates = enumerate_interfaces()
    if not candidates:
        pids = ", ".join(f"{VENDOR_ID:04x}:{pid:04x}" for pid in product_ids())
        raise RuntimeError(
            f"Teclado não encontrado (procurei {pids}). "
            "Conecte pelo cabo USB ou pelo receptor 2.4G — no Bluetooth o canal "
            "da tela não é exposto. Se o seu modelo usa outro PID, veja "
            "'xshark probe' e a variável XSHARK_PRODUCT_IDS."
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
        self._dev = _open_path(self._path)
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
