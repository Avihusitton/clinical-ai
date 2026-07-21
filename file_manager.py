# -*- coding: utf-8 -*-
"""
ארכיטקטורת 3 התיקיות (Inbox / Archive / Error), כפי שסוכם עם ג'מיני.
תיקיית ה-inbox היא תחנת מעבר בלבד - בסוף כל ריצה היא אמורה להיות ריקה.
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
from pathlib import Path

log = logging.getLogger("file_manager")


def ensure_folders(cfg) -> None:
    for folder in cfg.all_working_folders():
        folder.mkdir(parents=True, exist_ok=True)


def move_to_archive(path: Path, archive_dir: Path, inbox_dir: Path = None) -> Path:
    """קובץ שעבר את כל הצינור בהצלחה. מוסיפים תאריך עיבוד לשם הקובץ ומשמרים היררכיה."""
    today = dt.date.today().isoformat()
    if inbox_dir and path.is_relative_to(inbox_dir):
        rel_parent = path.relative_to(inbox_dir).parent
        dest_dir = archive_dir / rel_parent
    else:
        dest_dir = archive_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _avoid_collision(dest_dir / f"{path.stem}_processed_{today}{path.suffix}")
    shutil.move(str(path), str(dest))
    log.info("הועבר לארכיון: %s", dest.name)
    return dest


def move_to_error(path: Path, error_dir: Path, reason: str, inbox_dir: Path = None) -> Path:
    """קובץ שנכשל. מועבר לתיקיית השגיאות; הסיבה נכתבת ללוג ולדוח."""
    if inbox_dir and path.is_relative_to(inbox_dir):
        rel_parent = path.relative_to(inbox_dir).parent
        dest_dir = error_dir / rel_parent
    else:
        dest_dir = error_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _avoid_collision(dest_dir / path.name)
    shutil.move(str(path), str(dest))
    log.error("הועבר ל-docs_error (%s): %s", reason, dest.name)
    return dest


def _avoid_collision(dest: Path) -> Path:
    """אם כבר קיים קובץ באותו שם ביעד, מוסיפים מונה - לא דורסים בטעות."""
    if not dest.exists():
        return dest
    stem, suffix, i = dest.stem, dest.suffix, 2
    while True:
        candidate = dest.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1
