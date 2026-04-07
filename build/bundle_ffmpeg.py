#!/usr/bin/env python3
"""
FFmpeg Bundler — Downloads static FFmpeg binaries for all target platforms
and places them in the ffmpeg/ directory for PyInstaller bundling.

Usage:
    python build/bundle_ffmpeg.py [--platform darwin|win32|linux] [--all]
"""

from __future__ import annotations

# Ensure UTF-8 output on Windows (cp1252 default can't encode ✓ → etc.)
import io
import sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import argparse
import os
import platform as _platform
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

# ─── Download URLs for static FFmpeg builds ───────────────────────────────────

FFMPEG_URLS: dict[str, dict] = {
    "darwin_x86_64": {
        "url": "https://evermeet.cx/ffmpeg/getrelease/zip",
        "extract": "zip",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
    },
    "darwin_arm64": {
        # Use homebrew or compile for arm64; this is a placeholder
        "url": None,
        "note": "Build from source or use homebrew: brew install ffmpeg",
    },
    "win32": {
        "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "extract": "zip",
        "ffmpeg": "ffmpeg.exe",
        "ffprobe": "ffprobe.exe",
    },
    "linux_x86_64": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "extract": "tar.xz",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
    },
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_DIR = PROJECT_ROOT / "ffmpeg"


def download_for_platform(platform: str) -> bool:
    """Download FFmpeg binaries for a specific platform."""
    info = FFMPEG_URLS.get(platform)
    if not info:
        print(f"Unknown platform: {platform}")
        return False

    if info["url"] is None:
        print(f"Skipping {platform}: {info.get('note', 'No URL')}")
        return False

    dest_dir = FFMPEG_DIR / platform.split("_")[0]  # "darwin", "win32", "linux"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading FFmpeg for {platform}...")
    print(f"  URL: {info['url']}")
    print(f"  Destination: {dest_dir}")

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "ffmpeg_archive"

        # Download
        try:
            urlretrieve(info["url"], str(archive_path))
        except Exception as e:
            print(f"  Download failed: {e}")
            return False

        # Extract
        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir()

        if info["extract"] == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        elif info["extract"] == "tar.xz":
            try:
                subprocess.run(
                    ["tar", "-xf", str(archive_path), "-C", str(extract_dir)],
                    check=True,
                    capture_output=True,
                )
            except FileNotFoundError:
                print("  Error: tar not found. Install xz-utils.")
                return False
            except subprocess.CalledProcessError as e:
                print(f"  Extraction failed: {e.stderr.decode()}")
                return False
        else:
            print(f"  Unknown archive format: {info['extract']}")
            return False

        # Find and copy binaries
        ffmpeg_bin = None
        ffprobe_bin = None
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f == info["ffmpeg"] and ffmpeg_bin is None:
                    ffmpeg_bin = Path(root) / f
                if f == info["ffprobe"] and ffprobe_bin is None:
                    ffprobe_bin = Path(root) / f

        if ffmpeg_bin and ffmpeg_bin.exists():
            dest = dest_dir / info["ffmpeg"]
            shutil.copy2(ffmpeg_bin, dest)
            if platform.startswith("linux"):
                os.chmod(dest, 0o755)
            print(f"  ✓ Copied {info['ffmpeg']} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            print(f"  ✗ Could not find {info['ffmpeg']} in archive")
            return False

        if ffprobe_bin and ffprobe_bin.exists():
            dest = dest_dir / info["ffprobe"]
            shutil.copy2(ffprobe_bin, dest)
            if platform.startswith("linux"):
                os.chmod(dest, 0o755)
            print(f"  ✓ Copied {info['ffprobe']} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            print(f"  ✗ Could not find {info['ffprobe']} in archive")

    return True


def copy_system_binaries() -> bool:
    """Copy system ffmpeg/ffprobe to current platform's ffmpeg/ dir."""
    system = _platform.system().lower()
    plat_dir = "darwin" if system == "darwin" else "win32" if system == "windows" else "linux"
    dest_dir = FFMPEG_DIR / plat_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    found = False
    for name in ["ffmpeg", "ffprobe"]:
        binary = shutil.which(name)
        if binary:
            dest = dest_dir / Path(binary).name
            shutil.copy2(binary, dest)
            print(f"  ✓ Copied system {name} → {dest}")
            found = True
        else:
            print(f"  ✗ {name} not found in PATH")

    return found


def main():
    parser = argparse.ArgumentParser(description="Bundle FFmpeg binaries")
    parser.add_argument(
        "--platform",
        choices=["darwin_x86_64", "darwin_arm64", "win32", "linux_x86_64"],
        help="Target platform (default: current system)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Download for all platforms"
    )
    parser.add_argument(
        "--from-system", action="store_true",
        help="Copy ffmpeg from system PATH instead of downloading",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  FFmpeg Bundler")
    print("=" * 60)

    if args.from_system:
        print("\nCopying from system PATH...")
        if copy_system_binaries():
            print("\nDone. Binaries placed in ffmpeg/<platform>/")
        else:
            print("\nFailed to find system ffmpeg.")
            sys.exit(1)
        return

    if args.all:
        platforms = [p for p in FFMPEG_URLS if FFMPEG_URLS[p]["url"] is not None]
    elif args.platform:
        platforms = [args.platform]
    else:
        # Detect current
        system = _platform.system().lower()
        machine = _platform.machine().lower()
        if system == "darwin":
            platforms = ["darwin_arm64" if machine in ("arm64", "aarch64") else "darwin_x86_64"]
        elif system == "windows":
            platforms = ["win32"]
        elif system == "linux":
            platforms = ["linux_x86_64"]
        else:
            print(f"Cannot detect platform: {system}/{machine}")
            sys.exit(1)

    success_count = 0
    for plat in platforms:
        if download_for_platform(plat):
            success_count += 1

    print(f"\n{'=' * 60}")
    print(f"  {success_count}/{len(platforms)} platform(s) completed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
