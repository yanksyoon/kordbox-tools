"""Playlist parsing and track backup engine."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class PlaylistTrack:
    """A single track referenced in a playlist."""
    original_path: str              # Path as written in the playlist
    found_path: Optional[str]       # Resolved absolute path on disk, or None
    exists: bool


@dataclass
class BackupReport:
    """Summary of a backup operation."""
    total: int = 0
    copied: int = 0
    skipped: int = 0
    missing: int = 0
    failed: int = 0
    missing_log: list[str] = field(default_factory=list)
    output_dir: str = ""


def parse_m3u8(filepath: str) -> list[str]:
    """
    Parse an M3U8/M3U playlist and return list of track paths.

    Skips ``#EXTM3U``, ``#EXTINF``, blank lines, and comments.
    """
    tracks: list[str] = []
    path = Path(filepath)
    if not path.is_file():
        return tracks

    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip().rstrip("\r")
            if not line or line.startswith("#"):
                continue
            tracks.append(line)
    return tracks


def parse_txt_playlist(filepath: str) -> list[str]:
    """
    Parse a tab-delimited TXT playlist (legacy format).

    Expects columns: num, artwork, bpm, track_title, key, time, genre,
    artist, album, rating, date_added.
    """
    tracks: list[str] = []
    path = Path(filepath)
    if not path.is_file():
        return tracks

    with open(path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            num = parts[0].strip()
            if num == "#":
                continue
            track_title = parts[3].strip()
            if track_title:
                tracks.append(track_title)
    return tracks


def parse_playlist(filepath: str) -> list[str]:
    """Auto-detect playlist format and parse."""
    ext = Path(filepath).suffix.lower().lstrip(".")
    if ext in ("m3u8", "m3u"):
        return parse_m3u8(filepath)
    if ext == "txt":
        return parse_txt_playlist(filepath)
    return []


def find_track(
    track_path: str,
    search_dirs: list[str],
) -> Optional[str]:
    """
    Smart track search strategy:
      1. Absolute path that exists → return it
      2. Exact filename match (case-insensitive) in search dirs
      3. Partial filename match
      4. Match without extension against common audio formats
    """
    # Strategy 1: absolute path
    if os.path.isabs(track_path) and os.path.isfile(track_path):
        return track_path

    filename = Path(track_path).name.strip()
    if not filename:
        return None

    for search_dir in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.is_dir():
            continue

        # Strategy 2: exact case-insensitive match
        found = _find_file_case_insensitive(dir_path, filename)
        if found:
            return str(found)

        # Strategy 3: partial match
        found = _find_file_partial(dir_path, filename)
        if found:
            return str(found)

        # Strategy 4: extension-agnostic match
        no_ext = Path(filename).stem
        if no_ext:
            found = _find_file_no_ext(dir_path, no_ext)
            if found:
                return str(found)

    return None


def backup_tracks(
    tracks: list[PlaylistTrack],
    output_dir: str,
    organize_by_playlist: bool = False,
    skip_existing: bool = True,
    playlist_name: Optional[str] = None,
    log_missing: bool = False,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> BackupReport:
    """
    Copy tracks to backup directory.

    Parameters
    ----------
    tracks : list[PlaylistTrack]
        Resolved tracks with found paths.
    output_dir : str
        Destination directory.
    organize_by_playlist : bool
        If True, create a subfolder per playlist.
    skip_existing : bool
        Skip files that already exist and are identical.
    playlist_name : str | None
        Name used for subfolder when organizing.
    log_missing : bool
        Collect missing track paths in report.
    on_progress : callable(current, total, message) | None
        Progress callback for GUI.
    """
    report = BackupReport(output_dir=output_dir)
    report.total = len(tracks)

    dest_base = Path(output_dir)
    if organize_by_playlist and playlist_name:
        dest_dir = dest_base / _safe_dirname(playlist_name)
    else:
        dest_dir = dest_base
    dest_dir.mkdir(parents=True, exist_ok=True)

    for i, track in enumerate(tracks):
        track_name = Path(track.original_path).name
        if on_progress:
            on_progress(i, report.total, track_name)

        if not track.exists or track.found_path is None:
            report.missing += 1
            if log_missing:
                report.missing_log.append(
                    f"{playlist_name or 'unknown'}: {track.original_path}"
                )
            continue

        src = Path(track.found_path)
        dst = dest_dir / src.name

        # Handle duplicates
        if dst.exists():
            if skip_existing and _files_identical(str(src), str(dst)):
                report.skipped += 1
                continue
            # Rename with counter
            dst = _unique_path(dest_dir, src.stem, src.suffix)

        try:
            shutil.copy2(str(src), str(dst))
            report.copied += 1
        except (OSError, shutil.Error):
            report.failed += 1

    return report


def resolve_tracks(
    track_paths: list[str],
    music_dirs: list[str],
) -> list[PlaylistTrack]:
    """Convert raw path strings into resolved PlaylistTrack objects."""
    results: list[PlaylistTrack] = []
    for path_str in track_paths:
        found = find_track(path_str, music_dirs)
        results.append(PlaylistTrack(
            original_path=path_str,
            found_path=found,
            exists=found is not None,
        ))
    return results


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _find_file_case_insensitive(directory: Path, filename: str) -> Optional[Path]:
    for item in directory.iterdir():
        if item.is_file() and item.name.lower() == filename.lower():
            return item
    return None


def _find_file_partial(directory: Path, filename: str) -> Optional[Path]:
    for item in directory.iterdir():
        if item.is_file() and filename.lower() in item.name.lower():
            return item
    return None


def _find_file_no_ext(directory: Path, stem: str) -> Optional[Path]:
    audio_ext = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a", ".aac", ".alac"}
    for item in directory.iterdir():
        if item.is_file() and stem.lower() in item.stem.lower():
            if item.suffix.lower() in audio_ext:
                return item
    return None


def _files_identical(a: str, b: str) -> bool:
    try:
        return filecmp_cmp(a, b)
    except OSError:
        return False


def filecmp_cmp(a: str, b: str) -> bool:
    """Compare two files byte-by-byte."""
    import filecmp
    return filecmp.cmp(a, b, shallow=False)


def _safe_dirname(name: str) -> str:
    """Sanitize a string for use as a directory name."""
    import re
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return safe.strip()[:100]


def _unique_path(directory: Path, stem: str, suffix: str) -> Path:
    """Generate a unique path by appending _1, _2, etc."""
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate
