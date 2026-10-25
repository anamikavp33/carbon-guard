"""Validate, store and fingerprint uploaded images.

sha256  : exact duplicate detection (identical file bytes). Stored as `image_hash`.
dHash   : perceptual "difference hash" (64 bit). Visually similar images give hashes that
          differ in only a few bits, even after resizing or re-compression.
"""
import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from PIL import Image, UnidentifiedImageError
from config import settings

ALLOWED = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class ImageError(ValueError):
    pass


@dataclass
class StoredImage:
    filename: str
    path: str
    url: str
    sha256: str
    dhash: str
    width: int
    height: int


def dhash(img: Image.Image, size: int = 8) -> str:
    small = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(small.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left, right = px[row * (size + 1) + col], px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"


def hamming(hex_a: str, hex_b: str) -> int:
    return bin(int(hex_a, 16) ^ int(hex_b, 16)).count("1")


def save_image(raw: bytes) -> StoredImage:
    """Check that `raw` is a real JPEG/PNG/WEBP image within the size limit, then store it."""
    if not raw:
        raise ImageError("The image file is empty")
    if len(raw) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise ImageError(f"The image is larger than {settings.MAX_IMAGE_MB} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()                              # checks the file is really an image
        img = Image.open(io.BytesIO(raw))         # verify() invalidates the object; reopen
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise ImageError("The uploaded file is not a valid image (use JPEG, PNG or WEBP)")
    if fmt not in ALLOWED:
        raise ImageError("Only JPEG, PNG or WEBP images are accepted")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ALLOWED[fmt]}"   # random name: never the user's file name
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(raw)
    return StoredImage(
        filename=filename, path=path, url=f"/uploads/{filename}",
        sha256=hashlib.sha256(raw).hexdigest(), dhash=dhash(img),
        width=img.width, height=img.height,
    )
