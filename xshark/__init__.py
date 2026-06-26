"""xshark — controle Linux da tela TFT do Attack Shark X85 Pro."""

from .device import PRODUCT_ID, VENDOR_ID, XSharkDevice, find_vendor_path

__all__ = ["VENDOR_ID", "PRODUCT_ID", "XSharkDevice", "find_vendor_path"]
__version__ = "0.0.1"
