"""Local exercise image storage for the vendored free-exercise-db dataset.

JSON image paths look like ``Barbell_Squat/0.jpg``. In the upstream repo those
files live at ``exercises/Barbell_Squat/0.jpg``. This module copies them into a
persistent directory and serves them from ``/media/exercises/...`` so the UI
never fetches GitHub or a CDN at page load.
"""

from __future__ import annotations

import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

import httpx

from app.config import DATA_DIR, ROOT_DIR

log = logging.getLogger(__name__)

MEDIA_URL_PREFIX = "/media/exercises"
THUMB_MAX = 160
MARKER_NAME = ".complete"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
# Official dataset archive. Used only during import, never as an <img> src.
ARCHIVE_URL = "https://github.com/yuhonas/free-exercise-db/archive/refs/heads/main.tar.gz"
GITHUB_IMAGE_PREFIXES = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/",
    "https://github.com/yuhonas/free-exercise-db/raw/main/exercises/",
    "https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/",
)


def get_images_dir() -> Path:
    env = os.getenv("EXERCISE_IMAGES_DIR")
    if env:
        return Path(env)
    return DATA_DIR / "exercise-images"


def get_bundle_dir() -> Path | None:
    env = os.getenv("EXERCISE_IMAGES_BUNDLE")
    if env:
        path = Path(env)
        return path if path.exists() else None
    for candidate in (
        ROOT_DIR / "seed_data" / "exercise-images",
        Path("/app/seed_data/exercise-images"),
    ):
        if candidate.exists():
            return candidate
    return None


def images_ready(root: Path | None = None) -> bool:
    root = root or get_images_dir()
    if (root / MARKER_NAME).exists():
        return True
    return any(p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES for p in _iter_full_images(root))


def _iter_full_images(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if "thumbs" in path.relative_to(root).parts:
            continue
        yield path


def normalize_stored_path(value: str | None) -> str | None:
    """Turn a DB/JSON image value into a relative path under the images dir."""
    if not value or not isinstance(value, str):
        return None
    stored = value.strip().replace("\\", "/")
    if not stored:
        return None
    for prefix in GITHUB_IMAGE_PREFIXES:
        if stored.startswith(prefix):
            stored = stored[len(prefix) :]
            break
    if stored.startswith(MEDIA_URL_PREFIX + "/"):
        stored = stored[len(MEDIA_URL_PREFIX) + 1 :]
        if stored.startswith("thumbs/"):
            stored = stored[len("thumbs/") :]
    if stored.startswith("http://") or stored.startswith("https://"):
        return None
    stored = stored.lstrip("/")
    if not stored or ".." in Path(stored).parts:
        return None
    return stored


def local_file_for(stored: str, *, thumb: bool = False, root: Path | None = None) -> Path:
    root = root or get_images_dir()
    rel = Path(stored)
    return (root / "thumbs" / rel) if thumb else (root / rel)


def public_url_for(stored: str, *, thumb: bool = False) -> str:
    rel = stored.replace("\\", "/")
    if thumb:
        return f"{MEDIA_URL_PREFIX}/thumbs/{rel}"
    return f"{MEDIA_URL_PREFIX}/{rel}"


def resolve_image_url(stored: str | None, *, thumb: bool = False, root: Path | None = None) -> str | None:
    rel = normalize_stored_path(stored)
    if not rel:
        return None
    root = root or get_images_dir()
    if thumb:
        thumb_path = local_file_for(rel, thumb=True, root=root)
        if thumb_path.is_file():
            return public_url_for(rel, thumb=True)
        full_path = local_file_for(rel, thumb=False, root=root)
        if full_path.is_file():
            return public_url_for(rel, thumb=False)
        return None
    if local_file_for(rel, thumb=False, root=root).is_file():
        return public_url_for(rel, thumb=False)
    return None


def resolve_image_urls(values: list | None, *, thumb: bool = False, root: Path | None = None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        url = resolve_image_url(value, thumb=thumb, root=root)
        if url and url not in out:
            out.append(url)
    return out


def archive_image_relpath(member_name: str) -> str | None:
    """Map a tarball member to the JSON image path, e.g. Barbell_Squat/0.jpg."""
    parts = Path(member_name.replace("\\", "/")).parts
    if ".." in parts:
        return None
    try:
        idx = parts.index("exercises")
    except ValueError:
        return None
    rest = parts[idx + 1 :]
    if len(rest) != 2:
        return None
    folder, filename = rest
    if Path(filename).suffix.lower() not in IMAGE_SUFFIXES:
        return None
    if "/" in folder or "\\" in folder:
        return None
    return f"{folder}/{filename}"


def import_from_archive(dest: Path, url: str = ARCHIVE_URL) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    log.info("Downloading free-exercise-db images from %s", url)
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "free-exercise-db.tar.gz"
        with httpx.Client(follow_redirects=True, timeout=180.0) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with archive_path.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        copied = 0
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                rel = archive_image_relpath(member.name)
                if not rel:
                    continue
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                with extracted, target.open("wb") as handle:
                    shutil.copyfileobj(extracted, handle)
                copied += 1
    log.info("Imported %s exercise image files into %s", copied, dest)
    return copied


def copy_bundle(src: Path, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_mtime < path.stat().st_mtime:
            shutil.copy2(path, target)
            copied += 1
    return copied


def generate_thumbnails(root: Path | None = None) -> int:
    from PIL import Image

    root = root or get_images_dir()
    created = 0
    for path in _iter_full_images(root):
        thumb = root / "thumbs" / path.relative_to(root)
        if thumb.exists() and thumb.stat().st_mtime >= path.stat().st_mtime:
            continue
        thumb.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(path) as image:
                rgb = image.convert("RGB")
                rgb.thumbnail((THUMB_MAX, THUMB_MAX))
                rgb.save(thumb, "JPEG", quality=80, optimize=True)
            created += 1
        except OSError:
            log.warning("Could not create thumbnail for %s", path)
    return created


def mark_complete(root: Path) -> None:
    (root / MARKER_NAME).write_text("ok\n", encoding="utf-8")


def save_custom_image(exercise_id: int, data: bytes, filename: str | None = None) -> str:
    """Store an uploaded custom-exercise image and return the relative path."""
    from PIL import Image
    import io

    suffix = (Path(filename or "upload.jpg").suffix or ".jpg").lower()
    if suffix not in IMAGE_SUFFIXES:
        suffix = ".jpg"
    root = get_images_dir()
    rel = f"custom/{exercise_id}/0.jpg"
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(data)) as image:
        rgb = image.convert("RGB")
        rgb.save(dest, "JPEG", quality=88, optimize=True)
    generate_thumbnails(root)
    return rel


def ensure_local_images(*, allow_download: bool = False, dest: Path | None = None) -> dict[str, int]:
    """Copy or download images into the persistent directory and build thumbs."""
    dest = dest or get_images_dir()
    dest.mkdir(parents=True, exist_ok=True)
    stats = {"copied": 0, "downloaded": 0, "thumbs": 0}
    if (dest / MARKER_NAME).exists() and images_ready(dest):
        return stats
    bundle = get_bundle_dir()
    if bundle and bundle.resolve() != dest.resolve() and any(_iter_full_images(bundle)):
        stats["copied"] = copy_bundle(bundle, dest)
    if not images_ready(dest) and allow_download and os.getenv("FITNESS_TESTING") != "1":
        stats["downloaded"] = import_from_archive(dest)
    stats["thumbs"] = generate_thumbnails(dest)
    if images_ready(dest):
        mark_complete(dest)
    elif allow_download:
        log.warning("Exercise images are missing at %s; UI will use placeholders.", dest)
    return stats
