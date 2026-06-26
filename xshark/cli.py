"""CLI do xshark: probe, set-time, set-gif e playlist."""

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


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def _upload_image(path: str, width: int, height: int, xoff: int) -> int:
    """Carrega e envia uma imagem/GIF para a tela. Retorna o nº de frames enviados."""
    from .image import load_frames
    from .protocol import build_image_chunk, build_image_init, chunkify

    frames, interval = load_frames(path, width=width, height=height, visible_x=xoff)
    if len(frames) > 255:
        frames = frames[:255]

    frame_count = len(frames)
    size_per_frame = len(frames[0])
    buffer = b"".join(frames)

    with XSharkDevice() as dev:
        dev.send_feature(
            build_image_init(frame_count, interval, size_per_frame, width=width, height=height)
        )
        for frame_idx in range(frame_count):
            base = frame_idx * size_per_frame
            frame = buffer[base : base + size_per_frame]
            for chunk_idx, data in chunkify(frame):
                dev.send_feature(
                    build_image_chunk(frame_idx, frame_count, interval, chunk_idx, data)
                )
    return frame_count


def cmd_set_gif(args) -> int:
    try:
        n = _upload_image(args.path, args.width, args.height, args.xoff)
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao enviar imagem: {exc}", file=sys.stderr)
        return 1
    print(f"OK — {n} frame(s) enviado(s). Confira a telinha. 🦈")
    return 0


def cmd_playlist(args) -> int:
    import random
    import time
    from pathlib import Path

    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"Pasta não encontrada: {folder}", file=sys.stderr)
        return 1
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not files:
        print(f"Nenhuma imagem em {folder} ({', '.join(sorted(IMAGE_EXTS))})", file=sys.stderr)
        return 1

    print(
        f"Playlist: {len(files)} imagem(ns), {args.interval}s cada"
        f"{' (shuffle)' if args.shuffle else ''}. Ctrl+C para parar."
    )
    try:
        while True:
            order = list(files)
            if args.shuffle:
                random.shuffle(order)
            for f in order:
                try:
                    n = _upload_image(str(f), args.width, args.height, args.xoff)
                    print(f"  → {f.name} ({n} frame(s))")
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {f.name}: {exc}", file=sys.stderr)
                time.sleep(args.interval)
            if args.once:
                break
    except KeyboardInterrupt:
        print("\nPlaylist parada.")
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

    def add_geometry(p):
        p.add_argument("--width", type=int, default=138, help="largura do buffer (X85 Pro=138)")
        p.add_argument("--height", type=int, default=180, help="altura do buffer (X85 Pro=180)")
        p.add_argument("--xoff", type=int, default=0, help="coluna inicial visível (default 0)")

    p_gif = sub.add_parser("set-gif", help="envia uma imagem ou GIF para a tela")
    p_gif.add_argument("path", help="caminho do PNG/JPG/GIF")
    add_geometry(p_gif)
    p_gif.set_defaults(func=cmd_set_gif)

    p_pl = sub.add_parser("playlist", help="rotaciona imagens/GIFs de uma pasta na tela")
    p_pl.add_argument("dir", help="pasta com as imagens/GIFs")
    p_pl.add_argument("--interval", type=float, default=30, help="segundos por imagem (default 30)")
    p_pl.add_argument("--shuffle", action="store_true", help="ordem aleatória")
    p_pl.add_argument("--once", action="store_true", help="passa uma vez e para (não repete)")
    add_geometry(p_pl)
    p_pl.set_defaults(func=cmd_playlist)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
