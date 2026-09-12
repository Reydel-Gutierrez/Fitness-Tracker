"""Safe SQLite backup using the SQLite backup API (WAL-safe)."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup(db_path: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def restore(backup_path: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(backup_path)
    try:
        dst = sqlite3.connect(db_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="WAL-safe SQLite backup/restore")
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--db", default=str(Path("/data/fitness.db") if Path("/data/fitness.db").exists() else Path(__file__).resolve().parents[2] / "data" / "fitness.db"))
    parser.add_argument("--file", default=None)
    args = parser.parse_args()
    db_path = Path(args.db)
    if args.action == "backup":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = Path(args.file) if args.file else db_path.parent / "backups" / f"fitness-{stamp}.db"
        backup(db_path, dest)
        print(f"Backed up {db_path} -> {dest}")
    else:
        if not args.file:
            raise SystemExit("--file is required for restore")
        restore(Path(args.file), db_path)
        print(f"Restored {args.file} -> {db_path}")


if __name__ == "__main__":
    main()
