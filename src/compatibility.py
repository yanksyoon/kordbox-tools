"""CDJ compatibility checking engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.config import CDJ_MODELS, FAT32_MAX_SIZE, CDJModelSpecs
from src.metadata import AudioMetadata, extract_metadata
from src.utils import get_display_model_name, normalise_model_name


@dataclass(frozen=True)
class CompatibilityResult:
    """Result of a single file-vs-model compatibility check."""
    filepath: str
    model: str                 # display name, e.g. "CDJ-3000"
    model_key: str             # internal key, e.g. "cdj-3000"
    compatible: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: Optional[AudioMetadata] = None


def check_compatibility(
    filepath: str,
    model: str,
    metadata: Optional[AudioMetadata] = None,
) -> CompatibilityResult:
    """
    Check whether *filepath* is compatible with the given CDJ *model*.

    Parameters
    ----------
    filepath : str
        Path to the audio file.
    model : str
        CDJ model name (e.g. ``"CDJ-3000"`` or ``"cdj-3000"``).
    metadata : AudioMetadata | None
        Pre-extracted metadata, or ``None`` to extract automatically.
    """
    model_key = normalise_model_name(model)

    if model_key not in CDJ_MODELS:
        return CompatibilityResult(
            filepath=filepath,
            model=model,
            model_key=model_key,
            compatible=False,
            errors=[f"Unknown CDJ model: {model}"],
        )

    specs = CDJ_MODELS[model_key]
    display_name = get_display_model_name(model_key)

    import os
    if not os.path.isfile(filepath):
        return CompatibilityResult(
            filepath=filepath,
            model=display_name,
            model_key=model_key,
            compatible=False,
            errors=[f"File not found: {filepath}"],
        )

    file_ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    notes: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    compatible = True

    # --- Format check ---
    if file_ext not in specs.formats:
        compatible = False
        errors.append(f"Format {file_ext.upper()} is NOT supported by {display_name}")
        supported = ", ".join(sorted(specs.formats)).upper()
        notes.append(f"Supported formats: {supported}")
        return CompatibilityResult(
            filepath=filepath, model=display_name, model_key=model_key,
            compatible=False, errors=errors, warnings=warnings, notes=notes,
        )

    notes.append(f"Format {file_ext.upper()} is supported")

    # --- Metadata checks ---
    if metadata is None:
        metadata = extract_metadata(filepath)

    if metadata:
        compatible, errors, warnings, notes = _check_metadata_specs(
            metadata, specs, display_name, compatible, errors, warnings, notes,
        )
    else:
        warnings.append("Could not read audio metadata (ffprobe not available)")

    # --- Storage notes ---
    storage = []
    if specs.usb:
        storage.append("USB")
    if specs.sd_card:
        storage.append("SD Card")
    notes.append(f"Storage: {', '.join(storage)}")
    if specs.rekordbox:
        notes.append("Rekordbox compatible")

    return CompatibilityResult(
        filepath=filepath, model=display_name, model_key=model_key,
        compatible=compatible, errors=errors, warnings=warnings, notes=notes,
        metadata=metadata,
    )


def check_all_models(
    filepath: str,
    metadata: Optional[AudioMetadata] = None,
) -> dict[str, CompatibilityResult]:
    """Check file compatibility against all CDJ models.

    Returns dict mapping display model name → CompatibilityResult.
    """
    # Extract metadata once
    if metadata is None:
        import os
        if os.path.isfile(filepath):
            metadata = extract_metadata(filepath)

    results: dict[str, CompatibilityResult] = {}
    for model_key in CDJ_MODELS:
        display = get_display_model_name(model_key)
        results[display] = check_compatibility(filepath, model_key, metadata)
    return results


def find_compatible_models(
    filepath: str,
    metadata: Optional[AudioMetadata] = None,
) -> list[str]:
    """Return list of display model names that support this file."""
    results = check_all_models(filepath, metadata)
    return [name for name, r in results.items() if r.compatible]


# ─── Internal ─────────────────────────────────────────────────────────────────

def _check_metadata_specs(
    metadata: AudioMetadata,
    specs: CDJModelSpecs,
    display_name: str,
    compatible: bool,
    errors: list[str],
    warnings: list[str],
    notes: list[str],
) -> tuple[bool, list[str], list[str], list[str]]:
    """Validate metadata against CDJ specs, mutating result lists."""

    # Sample rate
    if metadata.sample_rate:
        if metadata.sample_rate in specs.sample_rates:
            notes.append(f"Sample rate: {metadata.sample_rate} Hz (supported)")
        else:
            compatible = False
            errors.append(f"Sample rate {metadata.sample_rate} Hz is NOT supported")
            rates = ", ".join(str(r) for r in sorted(specs.sample_rates))
            notes.append(f"Supported sample rates: {rates} Hz")

    # Bit depth
    if metadata.bit_depth:
        if metadata.bit_depth in specs.bit_depths:
            notes.append(f"Bit depth: {metadata.bit_depth}-bit (supported)")
        else:
            if metadata.format in ("wav", "aiff", "aif"):
                compatible = False
                errors.append(f"Bit depth {metadata.bit_depth}-bit is NOT supported")
                depths = ", ".join(str(d) for d in sorted(specs.bit_depths))
                notes.append(f"Supported bit depths: {depths}-bit")
            else:
                warnings.append(f"Bit depth {metadata.bit_depth}-bit may not be optimal")

    # Bitrate for lossy formats
    if metadata.format in {"mp3", "aac"} and metadata.bitrate > 0:
        bitrate_kbps = metadata.bitrate // 1000
        if bitrate_kbps > specs.max_bitrate:
            warnings.append(
                f"Bitrate {bitrate_kbps} kbps exceeds maximum {specs.max_bitrate} kbps"
            )
        else:
            notes.append(f"Bitrate: {bitrate_kbps} kbps (max: {specs.max_bitrate} kbps)")

    # Channels
    if metadata.channels:
        if metadata.channels <= 2:
            ch_label = "Stereo" if metadata.channels == 2 else "Mono"
            notes.append(f"Channels: {metadata.channels} ({ch_label})")
        else:
            warnings.append(
                f"File has {metadata.channels} channels; "
                f"CDJs typically support stereo (2 channels)"
            )

    # Duration
    if metadata.duration > 0:
        from src.utils import format_duration
        notes.append(f"Duration: {format_duration(metadata.duration)}")

    # File size
    if metadata.file_size > 0:
        from src.utils import format_size
        notes.append(f"File size: {format_size(metadata.file_size)}")
        if metadata.file_size > FAT32_MAX_SIZE:
            warnings.append("File exceeds 4 GB FAT32 limit — use exFAT formatted drive")

    return compatible, errors, warnings, notes
