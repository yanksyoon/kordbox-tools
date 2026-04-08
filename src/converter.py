"""Audio conversion engine — builds and runs ffmpeg commands."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from src.config import (
    CDJ_MODELS,
    CONVERSION_PRESETS,
    ConversionPreset,
    CDJModelSpecs,
)
from src.metadata import AudioMetadata, extract_metadata
from src.utils import (
    FFmpegNotFoundError,
    find_ffmpeg,
    format_size,
    get_display_model_name,
    normalise_model_name,
)


@dataclass
class ConversionTarget:
    """Target format specification for conversion."""
    format: str                          # "wav", "mp3", "flac", "aiff", "aac"
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    bitrate: Optional[str] = None        # e.g. "320k" for MP3/AAC


# Formats that are inherently lossy (discard audio information on encode)
LOSSY_FORMATS: frozenset[str] = frozenset({"mp3", "aac", "m4a"})
# Formats that are lossless (bit-perfect round-trip)
LOSSLESS_FORMATS: frozenset[str] = frozenset({"wav", "aiff", "flac"})


@dataclass
class ConversionResult:
    """Result of converting a single file."""
    input_path: str
    output_path: str
    success: bool
    error: str = ""
    input_size: int = 0
    output_size: int = 0
    skipped: bool = False               # Already compatible
    skipped_reason: str = ""


@dataclass
class ConversionReport:
    """Summary of a batch conversion."""
    total: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[ConversionResult] = field(default_factory=list)
    output_dir: str = ""


# ─── Target resolution ────────────────────────────────────────────────────────

def target_from_model(model: str) -> ConversionTarget:
    """Derive conversion target from a CDJ model's optimal format."""
    key = normalise_model_name(model)
    if key not in CDJ_MODELS:
        raise ValueError(f"Unknown CDJ model: {model}")
    specs: CDJModelSpecs = CDJ_MODELS[key]

    # Pick the most common sample rate
    sr = min(specs.sample_rates)
    bd = min(specs.bit_depths)

    return ConversionTarget(
        format="wav",
        sample_rate=sr,
        bit_depth=bd,
    )


def target_from_reference(filepath: str) -> ConversionTarget:
    """Derive target from a reference file's actual format."""
    meta = extract_metadata(filepath)
    if meta is None:
        raise ValueError(f"Cannot read reference file: {filepath}")

    ext = meta.format
    # Normalise aif → aiff
    if ext == "aif":
        ext = "aiff"

    return ConversionTarget(
        format=ext,
        sample_rate=meta.sample_rate if meta.sample_rate else None,
        bit_depth=meta.bit_depth,
    )


def target_from_preset(name: str) -> ConversionTarget:
    """Derive target from a named preset."""
    if name not in CONVERSION_PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(CONVERSION_PRESETS.keys())}")
    preset: ConversionPreset = CONVERSION_PRESETS[name]
    return ConversionTarget(
        format=preset.format,
        sample_rate=preset.sample_rate,
        bit_depth=preset.bit_depth,
        bitrate=preset.bitrate,
    )


# ─── Conversion logic ─────────────────────────────────────────────────────────

def resolve_prefer_lossless_target(
    source: AudioMetadata,
    target: ConversionTarget,
) -> ConversionTarget:
    """
    Override a lossy target with a lossless equivalent when prefer_lossless is enabled.

    Policy:
    - If the target is already lossless (wav, aiff, flac), return it unchanged.
    - If the target is lossy (mp3, aac, m4a), override to FLAC, preserving
      the source sample rate and bit depth.  This avoids lossy encoding
      regardless of whether the source itself is lossy or lossless:
      converting a lossy source to FLAC cannot restore quality, but it does
      prevent *further* quality loss from an additional lossy encode.

    Note: FLAC is preferred over WAV/AIFF because it is lossless yet
    produces significantly smaller files, while still being natively
    supported by modern Pioneer CDJ models (CDJ-2000NXS2, CDJ-3000).

    Parameters
    ----------
    source : AudioMetadata
        Metadata of the source file (used to preserve sample rate / bit depth).
    target : ConversionTarget
        Requested conversion target.

    Returns
    -------
    ConversionTarget
        The (possibly overridden) target.
    """
    if target.format.lower() not in LOSSY_FORMATS:
        # Target is already lossless — nothing to override.
        return target

    # Preserve source sample rate and bit depth where known.
    # For lossy sources (e.g. MP3), bit_depth is typically None; fall back to
    # 16-bit which is sufficient for that quality level.
    sr = source.sample_rate or target.sample_rate
    bd = source.bit_depth or 16

    return ConversionTarget(
        format="flac",
        sample_rate=sr,
        bit_depth=bd,
        bitrate=None,
    )

def needs_conversion(source: AudioMetadata, target: ConversionTarget) -> bool:
    """Check whether the source file already matches the target specs."""
    src_ext = source.format
    if src_ext == "aif":
        src_ext = "aiff"

    # Different format → needs conversion
    if src_ext != target.format:
        return True

    # Different sample rate
    if target.sample_rate and source.sample_rate != target.sample_rate:
        return True

    # Different bit depth (for lossless)
    if target.format in ("wav", "aiff") and target.bit_depth:
        if source.bit_depth != target.bit_depth:
            return True

    # Different bitrate (for lossy)
    if target.format in ("mp3", "aac") and target.bitrate:
        target_bps = _bitrate_to_bps(target.bitrate)
        if target_bps and source.bitrate != target_bps:
            return True

    return False


def convert_file(
    input_path: str,
    output_dir: str,
    target: ConversionTarget,
    overwrite: bool = False,
    prefer_lossless: bool = False,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> ConversionResult:
    """
    Convert a single audio file to the target format.

    Parameters
    ----------
    input_path : str
        Path to source file.
    output_dir : str
        Directory for output file.
    target : ConversionTarget
        Desired output format and settings.
    overwrite : bool
        Overwrite existing output file.
    prefer_lossless : bool
        When True, avoid lossy encoding whenever possible.  If the requested
        target is a lossy format (mp3, aac, m4a), the target is automatically
        overridden to FLAC so that no additional quality is sacrificed.
        Has no effect when the target is already a lossless format.
    on_progress : callable(progress_0_to_1, message) | None
        Progress callback.
    """
    result = ConversionResult(
        input_path=input_path,
        output_path="",
        success=False,
    )

    if not os.path.isfile(input_path):
        result.error = f"Input file not found: {input_path}"
        return result

    # Extract source metadata
    meta = extract_metadata(input_path)
    if meta:
        result.input_size = meta.file_size
        if prefer_lossless:
            target = resolve_prefer_lossless_target(meta, target)
        if not needs_conversion(meta, target):
            result.skipped = True
            result.skipped_reason = "Already compatible with target format"
            result.success = True
            return result

    # Determine output path
    stem = Path(input_path).stem
    result.output_path = str(Path(output_dir) / f"{stem}.{target.format}")

    if not overwrite and os.path.isfile(result.output_path):
        result.skipped = True
        result.skipped_reason = "Output file already exists"
        result.success = True
        return result

    # Build and run ffmpeg
    try:
        _run_ffmpeg(input_path, result.output_path, target, on_progress)
    except FFmpegNotFoundError as e:
        result.error = str(e)
        return result
    except subprocess.CalledProcessError as e:
        result.error = f"ffmpeg failed: {e}"
        return result
    except Exception as e:
        result.error = f"Conversion error: {e}"
        return result

    # Record output size
    if os.path.isfile(result.output_path):
        result.output_size = os.path.getsize(result.output_path)
        result.success = True

    return result


def convert_batch(
    input_files: list[str],
    output_dir: str,
    target: ConversionTarget,
    skip_compatible: bool = True,
    overwrite: bool = False,
    prefer_lossless: bool = False,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> ConversionReport:
    """
    Convert multiple files to the target format.

    Parameters
    ----------
    input_files : list[str]
        List of input file paths.
    output_dir : str
        Output directory.
    target : ConversionTarget
        Desired format.
    skip_compatible : bool
        Skip files already matching target.
    overwrite : bool
        Overwrite existing output.
    prefer_lossless : bool
        When True, avoid lossy encoding whenever possible (see convert_file).
    on_progress : callable(current, total, filename) | None
    """
    report = ConversionReport(output_dir=output_dir, total=len(input_files))
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i, filepath in enumerate(input_files):
        name = Path(filepath).name
        if on_progress:
            on_progress(i, report.total, name)

        result = convert_file(filepath, output_dir, target, overwrite, prefer_lossless)
        report.results.append(result)

        if result.skipped:
            report.skipped += 1
        elif result.success:
            report.converted += 1
        else:
            report.failed += 1

    return report


# ─── FFmpeg command builder ──────────────────────────────────────────────────

def build_ffmpeg_cmd(
    input_path: str,
    output_path: str,
    target: ConversionTarget,
    dither: bool = False,
) -> list[str]:
    """Build an ffmpeg command list for the given target.

    Parameters
    ----------
    input_path : str
        Source file path.
    output_path : str
        Destination file path.
    target : ConversionTarget
        Output format and encoding settings.
    dither : bool
        When True and the output format is WAV or AIFF at 16-bit, apply
        triangular dithering via the ``aresample`` filter.  Dithering
        minimises quantisation noise when reducing from a higher bit depth
        (e.g. 24-bit source → 16-bit output).
    """
    ffmpeg = str(find_ffmpeg())
    cmd = [ffmpeg, "-i", input_path]

    fmt = target.format.lower()

    if fmt == "mp3":
        cmd.extend(["-codec:a", "libmp3lame"])
        if target.bitrate:
            cmd.extend(["-b:a", target.bitrate])
        if target.sample_rate:
            cmd.extend(["-ar", str(target.sample_rate)])
    elif fmt == "wav":
        bd = target.bit_depth or 16
        cmd.extend(["-codec:a", f"pcm_s{bd}le"])
        if target.sample_rate:
            cmd.extend(["-ar", str(target.sample_rate)])
        if dither and bd == 16:
            cmd.extend(["-af", "aresample=resampler=swr:dither_method=triangular_hp"])
    elif fmt == "aiff":
        bd = target.bit_depth or 16
        cmd.extend(["-codec:a", f"pcm_s{bd}be"])
        if target.sample_rate:
            cmd.extend(["-ar", str(target.sample_rate)])
        if dither and bd == 16:
            cmd.extend(["-af", "aresample=resampler=swr:dither_method=triangular_hp"])
    elif fmt == "flac":
        cmd.extend(["-codec:a", "flac"])
        if target.sample_rate:
            cmd.extend(["-ar", str(target.sample_rate)])
        if target.bit_depth:
            cmd.extend(["-sample_fmt", f"s{target.bit_depth}"])
    elif fmt in ("aac", "m4a"):
        cmd.extend(["-codec:a", "aac"])
        if target.bitrate:
            cmd.extend(["-b:a", target.bitrate])
        if target.sample_rate:
            cmd.extend(["-ar", str(target.sample_rate)])
    else:
        cmd.extend(["-codec:a", "copy"])

    cmd.extend(["-y", output_path])
    return cmd


def _run_ffmpeg(
    input_path: str,
    output_path: str,
    target: ConversionTarget,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Execute ffmpeg with optional progress parsing."""
    # Get duration for progress calculation; also use source metadata to decide
    # whether to apply dithering (bit-depth reduction to 16-bit).
    meta = extract_metadata(input_path)
    duration = meta.duration if meta else 0

    dither = (
        target.format.lower() in ("wav", "aiff")
        and (target.bit_depth or 16) == 16
        and meta is not None
        and meta.bit_depth is not None
        and meta.bit_depth > 16
    )

    cmd = build_ffmpeg_cmd(input_path, output_path, target, dither=dither)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Read stderr for progress
    while True:
        line = process.stderr.readline()  # type: ignore[union-attr]
        if not line:
            break
        if duration > 0 and on_progress:
            time_match = re.search(
                r"time=(\d+):(\d+):(\d+\.\d+)", line
            )
            if time_match:
                current = (
                    int(time_match.group(1)) * 3600
                    + int(time_match.group(2)) * 60
                    + float(time_match.group(3))
                )
                progress = min(current / duration, 1.0)
                on_progress(progress, Path(input_path).name)

    process.wait()
    if process.returncode != 0:
        stderr_output = ""
        if process.stderr:
            stderr_output = process.stderr.read()
        raise subprocess.CalledProcessError(
            process.returncode, cmd, output=stderr_output
        )


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _bitrate_to_bps(bitrate_str: str) -> Optional[int]:
    """Convert '320k' → 320000."""
    match = re.match(r"(\d+)\s*k", bitrate_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 1000
    try:
        return int(bitrate_str)
    except ValueError:
        return None


def scan_audio_files(directory: str, recursive: bool = False) -> list[str]:
    """Find all audio files in a directory."""
    from src.config import AUDIO_EXTENSIONS
    results: list[str] = []
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return results

    pattern = "**/*" if recursive else "*"
    for item in dir_path.glob(pattern):
        if item.is_file() and item.suffix.lower().lstrip(".") in AUDIO_EXTENSIONS:
            results.append(str(item))
    return sorted(results)
