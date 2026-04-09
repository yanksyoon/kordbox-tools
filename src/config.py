"""CDJ model specifications, conversion presets, and constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

# ─── CDJ Model Specifications ───────────────────────────────────────────────

@dataclass(frozen=True)
class CDJModelSpecs:
    """Technical specifications for a Pioneer CDJ model."""
    formats: Set[str]
    sample_rates: Set[int]
    bit_depths: Set[int]
    max_bitrate: int          # kbps for lossy formats
    rekordbox: bool
    usb: bool
    usb_c: bool
    sd_card: bool


CDJ_MODELS: Dict[str, CDJModelSpecs] = {
    "cdj-3000x": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff", "flac", "alac"},
        sample_rates={44100, 48000, 88200, 96000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=True,
        sd_card=False,
    ),
    "cdj-3000": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff", "flac", "alac"},
        sample_rates={44100, 48000, 88200, 96000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=True,
    ),
    "cdj-2000nxs2": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff", "flac", "alac"},
        sample_rates={44100, 48000, 88200, 96000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=True,
    ),
    "cdj-2000nxs": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=True,
    ),
    "cdj-2000": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=True,
    ),
    "cdj-900nxs": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=False,
    ),
    "cdj-900": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=False,
    ),
    "cdj-850": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16, 24},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=False,
    ),
    "cdj-400": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16},
        max_bitrate=320,
        rekordbox=False,
        usb=True,
        usb_c=False,
        sd_card=False,
    ),
    "cdj-350": CDJModelSpecs(
        formats={"mp3", "aac", "wav", "aiff"},
        sample_rates={44100, 48000},
        bit_depths={16},
        max_bitrate=320,
        rekordbox=True,
        usb=True,
        usb_c=False,
        sd_card=False,
    ),
}

# ─── Conversion Presets ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConversionPreset:
    """Named conversion preset."""
    format: str
    sample_rate: int | None = None
    bit_depth: int | None = None
    bitrate: str | None = None


CONVERSION_PRESETS: Dict[str, ConversionPreset] = {
    "club": ConversionPreset(
        format="wav",
        sample_rate=44100,
        bit_depth=16,
    ),
    "high_quality": ConversionPreset(
        format="mp3",
        sample_rate=44100,
        bitrate="320k",
    ),
    "hires": ConversionPreset(
        format="flac",
        sample_rate=96000,
        bit_depth=24,
    ),
}

# ─── Constants ────────────────────────────────────────────────────────────────

AUDIO_EXTENSIONS: set[str] = {
    "mp3", "aac", "wav", "aiff", "aif", "flac", "alac", "m4a", "ogg", "wma", "opus",
}

PLAYLIST_EXTENSIONS: set[str] = {"m3u8", "m3u", "txt"}

FAT32_MAX_SIZE = 4 * 1024 * 1024 * 1024  # 4 GB
