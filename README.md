# CDJ Audio Toolkit

A cross-platform desktop application for Pioneer CDJ workflow management — check audio file compatibility, backup playlist tracks, and convert audio to optimal CDJ formats.

## Features

### ◉ Compatibility Checker
- Check audio files against **9 Pioneer CDJ models** (CDJ-3000, CDJ-2000NXS2, CDJ-2000NXS, CDJ-2000, CDJ-900NXS, CDJ-900, CDJ-850, CDJ-400, CDJ-350)
- Validates: format, sample rate, bit depth, bitrate, channels, file size
- Matrix view showing compatibility across all models at a glance
- Detailed error/warning messages per file-model pair

### ☰ Playlist Backup
- Parse **M3U8, M3U, and TXT** playlist formats
- Smart track finding: absolute paths → exact filename match → partial match → extension-agnostic search
- Organize by playlist (separate folders) or flat structure
- Skip duplicates, log missing tracks

### ⇄ Audio Converter
- Convert audio to CDJ-compatible formats with flexible target specification:
  - **Match CDJ model** — auto-derive optimal format from model specs
  - **Match reference file** — clone the format of a file you already like
  - **Preset** — Club Standard (WAV 44.1kHz/16-bit), High Quality (MP3 320k), Hi-Res (FLAC 96kHz/24-bit)
  - **Custom** — pick format, sample rate, bit depth, bitrate manually
- Skip already-compatible files, dry-run mode, progress tracking

## Installation

### Prerequisites
- **Python 3.10+**
- **ffmpeg** — required for audio analysis and conversion
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`
  - Windows: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use [winget](https://winget.run/pkg/Gyan/FFmpeg): `winget install Gyan.FFmpeg`

### From Source

```bash
# Clone the repository
git clone <repo-url>
cd kordbox

# Install dependencies
pip install -e ".[dev]"

# Run the GUI
python run_gui.py

# Or use the CLI
python -m src.cli --help
```

### Standalone Build (with bundled ffmpeg)

```bash
# Bundle ffmpeg from system PATH
python build/bundle_ffmpeg.py --from-system

# Build standalone app
pip install pyinstaller
pyinstaller build/build.spec

# Output: dist/CDJAudioToolkit/ (macOS) or dist/CDJAudioToolkit.exe (Windows)
```

## CLI Usage

```bash
# Check file compatibility
cdj-tool check track.flac
cdj-tool check track.mp3 --model cdj-3000
cdj-tool check ./music --recursive
cdj-tool check track.flac --json

# Backup playlist tracks
cdj-tool backup myset.m3u8
cdj-tool backup ./playlists/ --organize --music-dir /Volumes/DJ/music

# Convert audio
cdj-tool convert track.flac --model cdj-3000
cdj-tool convert track.flac --reference track_i_like.wav
cdj-tool convert myset.m3u8 --preset club --music-dir ./music
cdj-tool convert ./music --format flac --sample-rate 96000 --bit-depth 24
cdj-tool convert ./music --dry-run
cdj-tool convert track.wav --json
```

## CDJ Model Specifications

| Model | Formats | Sample Rates | Bit Depths | Rekordbox | SD Card |
|-------|---------|-------------|------------|-----------|---------|
| CDJ-3000 | MP3,AAC,WAV,AIFF,FLAC,ALAC | 44.1-192 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000NXS2 | MP3,AAC,WAV,AIFF,FLAC,ALAC | 44.1-96 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000NXS | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000 | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✓ |
| CDJ-900NXS | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-900 | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-850 | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-400 | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16 | ✗ | ✗ |
| CDJ-350 | MP3,AAC,WAV,AIFF | 44.1, 48 kHz | 16 | ✓ | ✗ |

## Recommended Conversion Presets

| Preset | Format | Sample Rate | Bit Depth | Use Case |
|--------|--------|-------------|-----------|----------|
| Club Standard | WAV | 44.1 kHz | 16-bit | Maximum club compatibility |
| High Quality | MP3 | 44.1 kHz | — | Small file size, good quality |
| Hi-Res | FLAC | 96 kHz | 24-bit | Audiophile, CDJ-3000 only |

## Architecture

```
src/                    # Core engine (CLI-compatible)
  config.py             # CDJ model specs, presets, constants
  metadata.py           # ffprobe wrapper, AudioMetadata dataclass
  compatibility.py      # Compatibility checking engine
  backup.py             # Playlist parsing and backup engine
  converter.py          # FFmpeg conversion engine
  cli.py                # argparse CLI (check/backup/convert)
  utils.py              # FFmpeg resolution, formatting utilities

gui/                    # PySide6 desktop application
  app.py                # Main window with tabs, drag-and-drop
  theme.py              # Dark QSS theme
  tabs/
    check_tab.py        # Compatibility matrix tab
    backup_tab.py       # Playlist backup tab
    convert_tab.py      # Audio conversion tab
  components/           # Reusable widgets (file selector, log viewer, etc.)

build/
  bundle_ffmpeg.py      # Download/copy ffmpeg binaries for bundling
  build.spec            # PyInstaller build configuration

tests/                  # Unit tests (85+ tests)
```

## Development

```bash
# Run tests
pytest tests/ -v

# Run GUI
python run_gui.py

# Run CLI
python -m src.cli check --help
```

## License

MIT
