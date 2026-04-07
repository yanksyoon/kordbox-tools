"""CLI entry point — cdj-tool with check / backup / convert subcommands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from src.compatibility import (
    check_all_models,
    check_compatibility,
    find_compatible_models,
)
from src.backup import (
    PlaylistTrack,
    backup_tracks,
    parse_m3u8,
    parse_txt_playlist,
    parse_playlist,
    resolve_tracks,
)
from src.config import CDJ_MODELS, CONVERSION_PRESETS, PLAYLIST_EXTENSIONS
from src.converter import (
    ConversionTarget,
    convert_batch,
    convert_file,
    scan_audio_files,
    target_from_model,
    target_from_preset,
    target_from_reference,
)
from src.metadata import extract_metadata
from src.utils import (
    FFmpegNotFoundError,
    format_size,
    get_display_model_name,
    normalise_model_name,
)


# ─── Main entry ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cdj-tool",
        description="CDJ Audio Toolkit — Check compatibility, backup playlists, convert audio",
    )
    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # ── check ──
    p_check = sub.add_parser("check", help="Check audio file compatibility with CDJ models")
    p_check.add_argument("path", help="File, directory, or playlist to check")
    p_check.add_argument("--model", "-m", help="Check against specific CDJ model (default: all)")
    p_check.add_argument("--recursive", "-r", action="store_true", help="Scan directories recursively")
    p_check.add_argument("--json", action="store_true", help="Output results as JSON")

    # ── backup ──
    p_backup = sub.add_parser("backup", help="Backup tracks from M3U8 playlists")
    p_backup.add_argument("playlist", help="Playlist file or directory of playlists")
    p_backup.add_argument("--music-dir", default="./music", help="Music search directory")
    p_backup.add_argument("--output-dir", default="./backup", help="Backup destination")
    p_backup.add_argument("--organize", action="store_true", help="Organize by playlist (subfolders)")
    p_backup.add_argument("--skip-existing", action="store_true", help="Skip already-backed-up files")
    p_backup.add_argument("--log-missing", help="Log missing tracks to file")

    # ── convert ──
    p_convert = sub.add_parser("convert", help="Convert audio to CDJ-compatible format")
    p_convert.add_argument("input", help="File, directory, or playlist to convert")
    p_convert.add_argument("--model", help="Convert to CDJ model's optimal format")
    p_convert.add_argument("--preset", choices=list(CONVERSION_PRESETS.keys()), help="Use built-in preset")
    p_convert.add_argument("--reference", help="Match format of this reference file")
    p_convert.add_argument("--format", dest="fmt", help="Manual output format (wav, mp3, flac, aiff, aac)")
    p_convert.add_argument("--sample-rate", type=int, help="Sample rate in Hz")
    p_convert.add_argument("--bit-depth", type=int, choices=[16, 24], help="Bit depth")
    p_convert.add_argument("--bitrate", help="MP3/AAC bitrate (e.g. 320k)")
    p_convert.add_argument("--output-dir", default="./output", help="Output directory")
    p_convert.add_argument("--music-dir", default="./music", help="Music dir when processing playlists")
    p_convert.add_argument("--skip-compatible", action="store_true", help="Skip already-compatible files")
    p_convert.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    p_convert.add_argument("--dry-run", action="store_true", help="Show what would be converted")
    p_convert.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "check":
        _cmd_check(args)
    elif args.command == "backup":
        _cmd_backup(args)
    elif args.command == "convert":
        _cmd_convert(args)


# ─── check subcommand ─────────────────────────────────────────────────────────

def _cmd_check(args) -> None:
    path = args.path

    if not os.path.exists(path):
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    files = _resolve_input_files(path, recursive=args.recursive)
    if not files:
        print("No audio files found.")
        return

    all_results = []

    for filepath in files:
        if args.model:
            result = check_compatibility(filepath, args.model)
            all_results.append({filepath: {args.model: _result_to_dict(result)}})
        else:
            results = check_all_models(filepath)
            all_results.append({filepath: {k: _result_to_dict(v) for k, v in results.items()}})

    if args.json:
        print(json.dumps(all_results, indent=2))
        return

    for entry in all_results:
        for filepath, model_results in entry.items():
            print(f"\n{'=' * 80}")
            print(f"File: {filepath}")
            print(f"{'=' * 80}")
            for model_name, result in model_results.items():
                status = "COMPATIBLE" if result["compatible"] else "INCOMPATIBLE"
                print(f"\n  {model_name}: {status}")
                for e in result.get("errors", []):
                    print(f"    ERROR: {e}")
                for w in result.get("warnings", []):
                    print(f"    WARNING: {w}")
                for n in result.get("notes", []):
                    print(f"    {n}")

    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY: {len(files)} file(s) checked")
    for entry in all_results:
        for filepath, model_results in entry.items():
            compat_count = sum(1 for r in model_results.values() if r["compatible"])
            total = len(model_results)
            print(f"  {Path(filepath).name}: compatible with {compat_count}/{total} models")


def _result_to_dict(result) -> dict:
    return {
        "compatible": result.compatible,
        "errors": result.errors,
        "warnings": result.warnings,
        "notes": result.notes,
    }


# ─── backup subcommand ────────────────────────────────────────────────────────

def _cmd_backup(args) -> None:
    music_dirs = [args.music_dir]
    output_dir = args.output_dir

    # Gather playlist files
    playlist_files = _resolve_playlists(args.playlist)
    if not playlist_files:
        print(f"No playlist files found: {args.playlist}")
        return

    print(f"Found {len(playlist_files)} playlist(s)")
    print(f"Music directory: {args.music_dir}")
    print(f"Backup directory: {output_dir}")
    print()

    total_copied = 0
    total_skipped = 0
    total_missing = 0

    for pl_file in playlist_files:
        pl_name = Path(pl_file).stem
        print(f"--- Playlist: {pl_name} ---")

        tracks_raw = parse_playlist(pl_file)
        tracks = resolve_tracks(tracks_raw, music_dirs)

        report = backup_tracks(
            tracks=tracks,
            output_dir=output_dir,
            organize_by_playlist=args.organize,
            skip_existing=args.skip_existing,
            playlist_name=pl_name,
            log_missing=args.log_missing is not None,
            on_progress=lambda i, total, name: print(f"  [{i+1}/{total}] {name}"),
        )

        total_copied += report.copied
        total_skipped += report.skipped
        total_missing += report.missing

        print(f"  Copied: {report.copied}, Skipped: {report.skipped}, Missing: {report.missing}")
        if report.missing_log and args.log_missing:
            with open(args.log_missing, "a") as f:
                for line in report.missing_log:
                    f.write(line + "\n")
        print()

    print(f"Total: {total_copied} copied, {total_skipped} skipped, {total_missing} missing")


# ─── convert subcommand ───────────────────────────────────────────────────────

def _cmd_convert(args) -> None:
    # Resolve target
    target = _resolve_conversion_target(args)

    # Gather input files
    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: Path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    files = _resolve_input_files_with_playlists(input_path, music_dir=args.music_dir)
    if not files:
        print("No audio files found.")
        return

    if args.dry_run:
        print(f"Dry run — would convert {len(files)} file(s):")
        print(f"  Target: {target.format}", end="")
        if target.sample_rate:
            print(f" {target.sample_rate}Hz", end="")
        if target.bit_depth:
            print(f" {target.bit_depth}-bit", end="")
        if target.bitrate:
            print(f" {target.bitrate}", end="")
        print()
        for f in files:
            print(f"  {f}")
        return

    report = convert_batch(
        input_files=files,
        output_dir=args.output_dir,
        target=target,
        skip_compatible=args.skip_compatible,
        overwrite=args.overwrite,
        on_progress=lambda i, total, name: print(f"  [{i+1}/{total}] {name}"),
    )

    if args.json:
        output = {
            "total": report.total,
            "converted": report.converted,
            "skipped": report.skipped,
            "failed": report.failed,
            "output_dir": report.output_dir,
            "results": [
                {
                    "input": r.input_path,
                    "output": r.output_path,
                    "success": r.success,
                    "skipped": r.skipped,
                    "skipped_reason": r.skipped_reason,
                    "error": r.error,
                    "input_size": format_size(r.input_size) if r.input_size else None,
                    "output_size": format_size(r.output_size) if r.output_size else None,
                }
                for r in report.results
            ],
        }
        print(json.dumps(output, indent=2))
        return

    print(f"\nConverted: {report.converted}, Skipped: {report.skipped}, Failed: {report.failed}")
    print(f"Output directory: {report.output_dir}")
    for r in report.results:
        if r.skipped:
            print(f"  ⊘ {Path(r.input_path).name} — {r.skipped_reason}")
        elif r.success:
            inp = format_size(r.input_size) if r.input_size else "?"
            out = format_size(r.output_size) if r.output_size else "?"
            print(f"  ✓ {Path(r.input_path).name} → {Path(r.output_path).name} ({inp} → {out})")
        else:
            print(f"  ✗ {Path(r.input_path).name} — {r.error}")


def _resolve_conversion_target(args) -> "ConversionTarget":
    """Priority: --reference > --model > --preset > --format > default."""
    if args.reference:
        return target_from_reference(args.reference)
    if args.model:
        return target_from_model(args.model)
    if args.preset:
        return target_from_preset(args.preset)
    if args.fmt:
        return ConversionTarget(
            format=args.fmt,
            sample_rate=args.sample_rate,
            bit_depth=args.bit_depth,
            bitrate=args.bitrate,
        )
    # Default: WAV 44.1kHz 16-bit
    return ConversionTarget(format="wav", sample_rate=44100, bit_depth=16)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_input_files(path: str, recursive: bool = False) -> list[str]:
    """Resolve a path to a list of audio file paths."""
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        return scan_audio_files(path, recursive=recursive)
    return []


def _resolve_input_files_with_playlists(path: str, music_dir: str = "./music") -> list[str]:
    """Like _resolve_input_files but also handle playlists."""
    if os.path.isfile(path):
        ext = Path(path).suffix.lower().lstrip(".")
        if ext in PLAYLIST_EXTENSIONS:
            raw = parse_playlist(path)
            resolved = resolve_tracks(raw, [music_dir])
            return [t.found_path for t in resolved if t.found_path]
        return [path]
    if os.path.isdir(path):
        return scan_audio_files(path, recursive=True)
    return []


def _resolve_playlists(path: str) -> list[str]:
    """Resolve path to a list of playlist files."""
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        results = []
        for item in sorted(Path(path).iterdir()):
            if item.is_file() and item.suffix.lower().lstrip(".") in PLAYLIST_EXTENSIONS:
                results.append(str(item))
        return results
    return []


if __name__ == "__main__":
    main()
