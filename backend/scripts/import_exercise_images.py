"""Download free-exercise-db images into a persistent local directory.

Does not run at page-load time. Use this during Docker build, first seed, or
when refreshing local image assets.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.exercise_images import (  # noqa: E402
    ARCHIVE_URL,
    ensure_local_images,
    generate_thumbnails,
    get_images_dir,
    images_ready,
    import_from_archive,
    mark_complete,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import free-exercise-db exercise images")
    parser.add_argument(
        "--dest",
        default=None,
        help="Directory to store images (default: data/exercise-images or /data/exercise-images)",
    )
    parser.add_argument(
        "--url",
        default=ARCHIVE_URL,
        help="Dataset archive URL used only for this import",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Only copy a local bundle and generate thumbnails",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if images already exist")
    args = parser.parse_args()
    dest = Path(args.dest) if args.dest else get_images_dir()
    dest.mkdir(parents=True, exist_ok=True)

    if args.skip_download:
        stats = ensure_local_images(allow_download=False, dest=dest)
    elif images_ready(dest) and not args.force:
        thumbs = generate_thumbnails(dest)
        mark_complete(dest)
        stats = {"copied": 0, "downloaded": 0, "thumbs": thumbs}
    else:
        downloaded = import_from_archive(dest, url=args.url)
        thumbs = generate_thumbnails(dest)
        mark_complete(dest)
        stats = {"copied": 0, "downloaded": downloaded, "thumbs": thumbs}
    print(
        f"Imported exercise images into {dest} "
        f"(copied={stats['copied']} downloaded={stats['downloaded']} thumbs={stats['thumbs']})"
    )


if __name__ == "__main__":
    main()
