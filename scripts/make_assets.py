"""Generate Tauri app icons and README download-button PNGs.

The download buttons match the style the user provided:
  * black rounded rectangle background
  * white platform glyph on the left (Apple / Windows-tiles / Tux)
  * "DOWNLOAD FOR" small-caps line on top, big bold platform name below

We render the platform glyphs from inline SVG path data (public-domain /
trademark fair-use for "Download for X" purposes) via reportlab + svglib,
then composite the result onto a Pillow-drawn button background. This keeps
the buttons crisp at any DPI and avoids shipping licensed raster art.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import cairo
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


# ── Inline SVG path data ─────────────────────────────────────────
# Apple logo (filled silhouette) — adapted from the public Apple icon in
# simple-icons (CC0 1.0 Universal). The path is centered on a 24×24 grid.
APPLE_PATH = (
    "M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35"
    "C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84"
    "1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09Z"
    "M12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25Z"
)


def _windows_paths() -> list[str]:
    """Windows logo: 4 tiles in a 2×2 grid, with a tiny gap, on a 24×24 grid."""
    g = 0.6  # gap
    s = (24 - 3 * g) / 2  # tile size
    x0, y0 = g, g
    return [
        f"M {x0} {y0} h {s} v {s} h -{s} Z",
        f"M {x0 + s + g} {y0} h {s} v {s} h -{s} Z",
        f"M {x0} {y0 + s + g} h {s} v {s} h -{s} Z",
        f"M {x0 + s + g} {y0 + s + g} h {s} v {s} h -{s} Z",
    ]






def _render_svg_glyph(paths: list[str], size_px: int, fill_rgb=(1, 1, 1)) -> Image.Image:
    """Render one or more 24×24 SVG paths into a transparent PIL image via cairo."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size_px, size_px)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    scale = size_px / 24.0
    ctx.scale(scale, scale)
    ctx.set_source_rgba(*fill_rgb, 1.0)
    for path_str in paths:
        ctx.new_path()
        _parse_svg_path(ctx, path_str)
        ctx.fill()
    buf = surface.get_data()
    img = Image.frombuffer("RGBA", (size_px, size_px), bytes(buf), "raw", "BGRA", 0, 1)
    return img




def _parse_svg_path(ctx, path: str) -> None:
    """Very small SVG path parser — supports the subset of commands used above:
    M, m, L, l, H, h, V, v, C, c, S, s, Q, q, Z, z."""
    import re

    tokens = re.findall(r"[MmLlHhVvCcSsQqZz]|-?\d*\.?\d+", path)
    i = 0
    cx = cy = 0.0
    start_x = start_y = 0.0
    last_ctrl = None
    cmd = None
    while i < len(tokens):
        tok = tokens[i]
        if tok in "MmLlHhVvCcSsQqZz":
            cmd = tok
            i += 1
            if cmd in "Zz":
                ctx.close_path()
                cx, cy = start_x, start_y
                continue
            continue
        rel = cmd.islower()
        if cmd in "Mm":
            x, y = float(tokens[i]), float(tokens[i + 1])
            if rel: x, y = cx + x, cy + y
            ctx.move_to(x, y)
            cx, cy = x, y
            start_x, start_y = x, y
            i += 2
            # Subsequent pairs are implicit L/l per SVG spec.
            cmd = "l" if rel else "L"
        elif cmd in "Ll":
            x, y = float(tokens[i]), float(tokens[i + 1])
            if rel: x, y = cx + x, cy + y
            ctx.line_to(x, y)
            cx, cy = x, y
            i += 2
        elif cmd in "Hh":
            x = float(tokens[i])
            if rel: x += cx
            ctx.line_to(x, cy)
            cx = x
            i += 1
        elif cmd in "Vv":
            y = float(tokens[i])
            if rel: y += cy
            ctx.line_to(cx, y)
            cy = y
            i += 1
        elif cmd in "Cc":
            x1, y1, x2, y2, x, y = (float(t) for t in tokens[i:i + 6])
            if rel:
                x1, y1 = cx + x1, cy + y1
                x2, y2 = cx + x2, cy + y2
                x, y = cx + x, cy + y
            ctx.curve_to(x1, y1, x2, y2, x, y)
            last_ctrl = (x2, y2)
            cx, cy = x, y
            i += 6
        elif cmd in "Ss":
            x2, y2, x, y = (float(t) for t in tokens[i:i + 4])
            if rel:
                x2, y2 = cx + x2, cy + y2
                x, y = cx + x, cy + y
            x1 = 2 * cx - last_ctrl[0] if last_ctrl else cx
            y1 = 2 * cy - last_ctrl[1] if last_ctrl else cy
            ctx.curve_to(x1, y1, x2, y2, x, y)
            last_ctrl = (x2, y2)
            cx, cy = x, y
            i += 4
        elif cmd in "Qq":
            x1, y1, x, y = (float(t) for t in tokens[i:i + 4])
            if rel:
                x1, y1 = cx + x1, cy + y1
                x, y = cx + x, cy + y
            # Convert quadratic → cubic.
            ctx.curve_to(
                cx + 2 / 3 * (x1 - cx), cy + 2 / 3 * (y1 - cy),
                x + 2 / 3 * (x1 - x), y + 2 / 3 * (y1 - y),
                x, y,
            )
            last_ctrl = (x1, y1)
            cx, cy = x, y
            i += 4
        else:
            i += 1


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Best-effort font lookup across Linux and macOS."""
    candidates_bold = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_reg = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates_bold if bold else candidates_reg:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _round_rect_button(
    glyph: Image.Image | None,
    headline: str,
    platform: str,
    width: int = 620,
    height: int = 180,
    bg: str = "#0a0a0a",
    fg: str = "#ffffff",
) -> Image.Image:
    """Compose one download button matching the reference design.

    When ``glyph`` is ``None`` the button is text-only and horizontally
    centered (used for the Linux badge — we couldn't render a Tux silhouette
    we were happy with, so we ship a clean text-only black box instead).
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background.
    radius = int(min(width, height) * 0.10)
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=bg)

    headline_font = _font(int(height * 0.13), bold=False)
    platform_font = _font(int(height * 0.27), bold=True)

    # "DOWNLOAD FOR" — small-caps, letter-spaced, sitting above the platform name.
    spaced = " ".join(list(headline.upper()))
    h_bbox = draw.textbbox((0, 0), spaced, font=headline_font)
    p_bbox = draw.textbbox((0, 0), platform, font=platform_font)
    h_h = h_bbox[3] - h_bbox[1]
    p_h = p_bbox[3] - p_bbox[1]
    h_w = h_bbox[2] - h_bbox[0]
    p_w = p_bbox[2] - p_bbox[0]
    gap = int(height * 0.04)
    block_h = h_h + gap + p_h
    block_top = (height - block_h) // 2 - int(h_bbox[1])

    if glyph is not None:
        glyph_h = int(height * 0.70)
        g = glyph.resize((glyph_h, glyph_h), Image.LANCZOS)
        gx = int(width * 0.07)
        gy = (height - glyph_h) // 2
        img.paste(g, (gx, gy), g)
        text_x_headline = gx + glyph_h + int(width * 0.06)
        text_x_platform = text_x_headline
    else:
        # Center the text block as a whole.
        block_w = max(h_w, p_w)
        text_x_headline = (width - block_w) // 2 + (block_w - h_w) // 2
        text_x_platform = (width - block_w) // 2 + (block_w - p_w) // 2

    draw.text((text_x_headline, block_top), spaced, fill="#cccccc", font=headline_font)
    draw.text((text_x_platform, block_top + h_h + gap), platform, fill=fg, font=platform_font)
    return img


# ── Icon factory for the Tauri bundle ──────────────────────────
def _tauri_icon(size: int) -> Image.Image:
    """Solid-color rounded square with a white serif 's' — generated procedurally."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 16
    radius = size // 5
    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad), radius=radius, fill="#2563eb",
    )
    # Center an 's' glyph.
    font = _font(int(size * 0.62), bold=True)
    bbox = draw.textbbox((0, 0), "s", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1] - int(size * 0.03)),
        "s", fill="white", font=font,
    )
    return img


def write_icons() -> None:
    out = ROOT / "app/src-tauri/icons"
    out.mkdir(parents=True, exist_ok=True)
    sizes = {"32x32.png": 32, "128x128.png": 128, "128x128@2x.png": 256}
    for name, sz in sizes.items():
        _tauri_icon(sz).save(out / name)
        print(f"  ✓ {out / name}  ({sz}x{sz})")
    master = _tauri_icon(512)
    master.save(out / "icon.png")
    master.resize((256, 256)).save(
        out / "icon.ico", format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"  ✓ {out / 'icon.ico'}")
    try:
        master.save(out / "icon.icns")
        print(f"  ✓ {out / 'icon.icns'}")
    except Exception as e:
        print(f"  ⚠ icon.icns: {e}; writing PNG fallback", file=sys.stderr)
        master.save(out / "icon.icns")


def write_download_badges() -> None:
    out = ROOT / "docs/assets"
    out.mkdir(parents=True, exist_ok=True)

    apple = _render_svg_glyph([APPLE_PATH], size_px=256)
    windows = _render_svg_glyph(_windows_paths(), size_px=256)
    # Linux: no glyph — see make_assets._round_rect_button for rationale.
    badges = [
        ("download-macos.png", apple, "Download for", "macOS"),
        ("download-windows.png", windows, "Download for", "Windows"),
        ("download-linux.png", None, "Download for", "Linux"),
    ]
    for fname, glyph, headline, platform in badges:
        img = _round_rect_button(glyph, headline, platform)
        img.save(out / fname)
        print(f"  ✓ {out / fname}  ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    print("→ icons")
    write_icons()
    print("→ download badges")
    write_download_badges()
