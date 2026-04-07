"""Shared utilities — ffmpeg resolution, formatting, path helpers."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Optional


class FFmpegNotFoundError(Exception):
    """Raised when ffmpeg/ffprobe cannot be located."""


def find_binary(name: str) -> Path:
    """
    Locate an executable binary in priority order:
      1. Bundled location (PyInstaller _MEIPASS or ffmpeg/<platform>/)
      2. System PATH

    Raises ``FFmpegNotFoundError`` if not found.
    """
    # --- 1. Bundled (PyInstaller) ---
    if getattr(__import__("sys"), "frozen", False):
        meipass = Path(getattr(__import__("sys"), "_MEIPASS", ""))
        if meipass.is_dir():
            bundled = meipass / "ffmpeg" / _platform_dir() / name
            if bundled.exists():
                return bundled

    # --- Dev-time bundled (relative to this file) ---
    dev_bundle = Path(__file__).resolve().parent.parent / "ffmpeg" / _platform_dir() / name
    if dev_bundle.exists():
        return dev_bundle

    # --- 2. System PATH ---
    found = shutil.which(name)
    if found:
        return Path(found)

    raise FFmpegNotFoundError(
        f"{name} not found. Install ffmpeg (brew install ffmpeg / apt install ffmpeg) "
        f"or place a static binary in ffmpeg/{_platform_dir()}/{name}"
    )


def find_ffmpeg() -> Path:
    """Locate the ffmpeg binary."""
    return find_binary(_ffmpeg_name())


def find_ffprobe() -> Path:
    """Locate the ffprobe binary."""
    return find_binary(_ffprobe_name())


def format_duration(seconds: float) -> str:
    """Format seconds as ``MM:SS`` or ``HH:MM:SS``."""
    if seconds < 0:
        seconds = 0
    total_secs = int(seconds)
    hrs = total_secs // 3600
    mins = (total_secs % 3600) // 60
    secs = total_secs % 60
    if hrs:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.1f} GB"


def normalise_model_name(name: str) -> str:
    """Normalise model name for lookup (lowercase, strip spaces)."""
    return name.lower().replace("_", "-").replace(" ", "-")


def get_display_model_name(key: str) -> str:
    """Convert internal key to display-friendly name."""
    mapping = {
        "cdj-3000": "CDJ-3000",
        "cdj-2000nxs2": "CDJ-2000NXS2",
        "cdj-2000nxs": "CDJ-2000NXS",
        "cdj-2000": "CDJ-2000",
        "cdj-900nxs": "CDJ-900NXS",
        "cdj-900": "CDJ-900",
        "cdj-850": "CDJ-850",
        "cdj-400": "CDJ-400",
        "cdj-350": "CDJ-350",
    }
    return mapping.get(key, key.upper())


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _platform_dir() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    if system == "windows":
        return "win32"
    if system == "linux":
        return "linux"
    return system


def _ffmpeg_name() -> str:
    return "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"


def _ffprobe_name() -> str:
    return "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"
