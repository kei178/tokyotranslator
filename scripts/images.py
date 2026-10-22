#!/usr/bin/env python3
"""One-off: resize and compress the recovered site images.

Usage: python3 -I scripts/images.py SRC_DIR OUT_DIR

SRC_DIR must contain profile.jpg, slider1.jpg, slider2.jpg, slider3.jpg
(the originals recovered from the Wayback Machine). OUT_DIR receives
hero.jpg / hero.webp (slider1), hero-2.jpg, hero-3.jpg, profile.jpg /
profile.webp. EXIF is stripped from every output.
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

HERO_WIDTH = 1600          # never upscaled: smaller originals keep their width
PROFILE_SIZE = (400, 400)
JPEG_Q = 80
WEBP_Q = 78


def load(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path))
    return img.convert("RGB")


def save_jpeg(img: Image.Image, path: Path, quality: int) -> None:
    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)


def save_webp(img: Image.Image, path: Path, quality: int) -> None:
    img.save(path, "WEBP", quality=quality, method=6)


def hero(src: Path, out_jpg: Path, out_webp: Path | None) -> None:
    img = load(src)
    if img.width > HERO_WIDTH:
        img = img.resize((HERO_WIDTH, round(img.height * HERO_WIDTH / img.width)), Image.LANCZOS)
    save_jpeg(img, out_jpg, JPEG_Q)
    if out_webp:
        save_webp(img, out_webp, WEBP_Q)


def profile(src: Path, out_jpg: Path, out_webp: Path) -> None:
    img = ImageOps.fit(load(src), PROFILE_SIZE, Image.LANCZOS, centering=(0.5, 0.5))
    save_jpeg(img, out_jpg, 85)
    save_webp(img, out_webp, 82)


def main(src_dir: str, out_dir: str) -> None:
    src, out = Path(src_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    hero(src / "slider1.jpg", out / "hero.jpg", out / "hero.webp")
    hero(src / "slider2.jpg", out / "hero-2.jpg", None)
    hero(src / "slider3.jpg", out / "hero-3.jpg", None)
    profile(src / "profile.jpg", out / "profile.jpg", out / "profile.webp")
    for p in sorted(out.iterdir()):
        print(f"{p.name:14} {p.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
