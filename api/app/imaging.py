"""Smaller copies of uploaded pictures, so a card in a list does not download a 5 MB original.

The public image routes take `?w=<width>`. A copy is made the first time it is asked for, stored next to the
original in object storage, and served from there afterwards. The original is never touched."""
import io

from anyio import to_thread
from fastapi import HTTPException, Query
from PIL import Image, ImageOps, UnidentifiedImageError

from .storage import Storage

# The only widths served. A fixed list keeps the number of stored copies small and cannot be used to fill the disk.
WIDTHS = (320, 480, 640, 960, 1280, 1600)


def width_param(w: int | None = Query(None, description="Serve a copy this many pixels wide: 320, 480, 640, 960, 1280 or 1600")) -> int | None:
    if w is not None and w not in WIDTHS:
        raise HTTPException(422, f"w must be one of {WIDTHS}")
    return w

# A file that claims to be enormous is refused instead of unpacked into memory.
Image.MAX_IMAGE_PIXELS = 60_000_000


def shrink(data: bytes, width: int) -> bytes | None:
    """The picture at `width` pixels wide as WebP, or None when it should be served as it is:
    already narrower, an animation, or not something Pillow can read."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, "is_animated", False):
                return None
            image = ImageOps.exif_transpose(image)
            if image.width <= width:
                return None
            height = max(1, round(image.height * width / image.width))
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
            out = io.BytesIO()
            image.save(out, "WEBP", quality=80, method=4)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None


async def variant(storage: Storage, key: str, width: int) -> tuple[bytes, str] | None:
    """The stored copy of the file at `key` at this width, made now if it does not exist yet.
    None means: serve the original."""
    copy_key = f"thumbs/{key}@{width}.webp"
    cached = await storage.get(copy_key)
    if cached is not None:
        return cached, "image/webp"
    original = await storage.get(key)
    if original is None:
        return None
    small = await to_thread.run_sync(shrink, original, width)
    if small is None:
        return None
    await storage.put(copy_key, small, "image/webp")
    return small, "image/webp"
