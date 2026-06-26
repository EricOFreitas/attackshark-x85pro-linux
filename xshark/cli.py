"""CLI do xshark.

Hoje só `probe` está funcional — os comandos de escrita aguardam o protocolo ser
confirmado (ver docs/PROTOCOL.md).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .device import PRODUCT_ID, VENDOR_ID, XSharkDevice, find_vendor_path

try:
    import hid
except ImportError:  # pragma: no cover
    hid = None


def cmd_probe(_args) -> int:
    if hid is None:
        print("Falta a dependência 'hid' (pip install hid).", file=sys.stderr)
        return 1

    infos = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not infos:
        print(f"Teclado {VENDOR_ID:04x}:{PRODUCT_ID:04x} não encontrado.", file=sys.stderr)
        return 1

    print(f"Encontrado {VENDOR_ID:04x}:{PRODUCT_ID:04x} — {len(infos)} interface(s):")
    for i in infos:
        print(
            f"  iface={i.get('interface_number'):>2}  "
            f"usage_page=0x{i.get('usage_page', 0):04x}  "
            f"usage=0x{i.get('usage', 0):04x}  path={i['path'].decode(errors='replace')}"
        )

    path = find_vendor_path()
    print(f"\nCanal vendor (tela): {path.decode(errors='replace')}")
    try:
        with XSharkDevice(path) as dev:
            data = dev.get_feature()
            print("get_feature_report:", data.hex(" "))
    except Exception as exc:  # noqa: BLE001
        print(f"(leitura falhou — normal se o protocolo exigir handshake: {exc})")
    return 0


def cmd_set_time(_args) -> int:
    import datetime

    from .protocol import build_set_time

    now = datetime.datetime.now()
    packet = build_set_time(now)
    print(f"Enviando set-time ({now:%Y-%m-%d %H:%M:%S})")
    print("pacote:", packet.hex(" "))
    try:
        with XSharkDevice() as dev:
            n = dev.send_feature(packet)
        print(f"OK — {n} bytes escritos no canal da tela.")
        print("Confira o relógio na telinha. 🦈")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Falha ao enviar: {exc}", file=sys.stderr)
        return 1


def cmd_set_gif(args) -> int:
    from .image import load_frames
    from .protocol import build_image_chunk, build_image_init, chunkify

    try:
        frames, interval = load_frames(
            args.path, width=args.width, height=args.height, visible_x=args.xoff
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao ler imagem: {exc}", file=sys.stderr)
        return 1

    if len(frames) > 255:
        print(f"GIF tem {len(frames)} frames; usando os primeiros 255.")
        frames = frames[:255]

    frame_count = len(frames)
    size_per_frame = len(frames[0])
    buffer = b"".join(frames)
    total_chunks = frame_count * ((size_per_frame + 55) // 56)
    print(
        f"Enviando {frame_count} frame(s) de {size_per_frame} bytes "
        f"(interval={interval}ms, ~{total_chunks} chunks)…"
    )

    try:
        with XSharkDevice() as dev:
            dev.send_feature(
                build_image_init(
                    frame_count, interval, size_per_frame,
                    width=args.width, height=args.height,
                )
            )
            for frame_idx in range(frame_count):
                base = frame_idx * size_per_frame
                frame = buffer[base : base + size_per_frame]
                for chunk_idx, data in chunkify(frame):
                    dev.send_feature(
                        build_image_chunk(frame_idx, frame_count, interval, chunk_idx, data)
                    )
    except Exception as exc:  # noqa: BLE001
        print(f"Falha no envio: {exc}", file=sys.stderr)
        return 1

    print("OK — imagem enviada. Confira a telinha. 🦈")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="xshark", description=__doc__)
    parser.add_argument("--version", action="version", version=f"xshark {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("probe", help="lista interfaces e lê um feature report").set_defaults(
        func=cmd_probe
    )
    sub.add_parser("set-time", help="sincroniza o relógio da tela").set_defaults(
        func=cmd_set_time
    )

    p_gif = sub.add_parser("set-gif", help="envia uma imagem ou GIF para a tela")
    p_gif.add_argument("path", help="caminho do PNG/JPG/GIF")
    p_gif.add_argument("--width", type=int, default=180, help="largura do buffer (X85 Pro=180)")
    p_gif.add_argument("--height", type=int, default=179, help="altura do buffer (X85 Pro=179)")
    p_gif.add_argument("--xoff", type=int, default=0, help="coluna inicial da área visível (default 0)")
    p_gif.set_defaults(func=cmd_set_gif)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
