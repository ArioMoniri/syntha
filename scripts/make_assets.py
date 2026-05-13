"""Generate the Tauri app icons and the README download-button PNGs."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent


def _icon(size: int) -> np.ndarray:
    """Return an (size, size, 4) RGBA array — stethoscope-pink rounded square
    with a white S serif glyph. Generated procedurally so we don't ship a
    raster asset we'd have to license."""
    fig, ax = plt.subplots(figsize=(size / 100, size / 100), dpi=100)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_alpha(0)
    # Rounded square background
    bg = FancyBboxPatch(
        (0.05, 0.05), 0.9, 0.9,
        boxstyle="round,pad=0,rounding_size=0.18",
        linewidth=0, facecolor="#2563eb",
    )
    ax.add_patch(bg)
    ax.text(
        0.5, 0.46, "s",
        ha="center", va="center", color="white",
        fontsize=size * 0.7, fontweight="bold",
        fontfamily="serif",
    )
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba()).copy()
    plt.close(fig)
    return img


def write_icons() -> None:
    out = ROOT / "app/src-tauri/icons"
    out.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    sizes = {
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 256,
    }
    for name, sz in sizes.items():
        arr = _icon(sz)
        Image.fromarray(arr, mode="RGBA").save(out / name)
        print(f"  ✓ {out / name}  ({sz}x{sz})")
    # macOS .icns and Windows .ico — derived from the 256px master.
    master = Image.fromarray(_icon(512), mode="RGBA")
    master.save(out / "icon.png")  # also used as fallback
    master.resize((256, 256)).save(out / "icon.ico", format="ICO",
                                    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"  ✓ {out / 'icon.ico'}")
    # icns: PIL supports writing if the build host has pillow-icns; otherwise
    # we just leave a PNG with the .icns extension — Tauri tolerates this in
    # dev, and CI will rebuild a proper icns on macOS runners.
    try:
        master.save(out / "icon.icns")
        print(f"  ✓ {out / 'icon.icns'}")
    except Exception as e:
        print(f"  ⚠ icon.icns: {e}; writing PNG fallback", file=sys.stderr)
        master.save(out / "icon.icns")


def write_download_badges() -> None:
    out = ROOT / "docs/assets"
    out.mkdir(parents=True, exist_ok=True)
    badges = [
        ("download-macos.png", "Download for macOS", "Apple Silicon · .dmg", "#1e293b", "#f8fafc"),
        ("download-windows.png", "Download for Windows", "x64 installer · .exe", "#1e3a8a", "#f8fafc"),
        ("download-linux.png", "Download for Linux", "AppImage · x86_64", "#7c2d12", "#f8fafc"),
    ]
    for fname, title, sub, bg, fg in badges:
        fig, ax = plt.subplots(figsize=(2.4, 0.64), dpi=200)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        bgp = FancyBboxPatch(
            (0.005, 0.06), 0.99, 0.88,
            boxstyle="round,pad=0,rounding_size=0.18",
            linewidth=0, facecolor=bg,
        )
        ax.add_patch(bgp)
        ax.text(0.05, 0.65, title, ha="left", va="center", color=fg,
                fontsize=11, fontweight="bold", fontfamily="sans-serif")
        ax.text(0.05, 0.30, sub, ha="left", va="center", color=fg,
                fontsize=8, fontfamily="sans-serif", alpha=0.75)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        fig.savefig(out / fname, dpi=200, transparent=True)
        plt.close(fig)
        print(f"  ✓ {out / fname}")


if __name__ == "__main__":
    print("→ icons")
    write_icons()
    print("→ download badges")
    write_download_badges()
