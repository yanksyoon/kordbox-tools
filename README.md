# CDJ Audio Toolkit

A cross-platform desktop application for Pioneer CDJ workflow management — check audio file compatibility, backup playlist tracks, and convert audio to optimal CDJ formats.

```
┌─────────────────────────────────────────────────────────┐
│  CDJ Audio Toolkit                          [_][□][✕]   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │ ◉ Check  │ │  Backup  │ │ Convert  │  ← Three tabs  │
│  └──────────┘ └──────────┘ └──────────┘                │
├─────────────────────────────────────────────────────────┤
│  Dark-themed GUI • Drag & drop • Real-time progress     │
└─────────────────────────────────────────────────────────┘
```

---

## Features

### ◉ Compatibility Checker
- Check audio files against **9 Pioneer CDJ models** (CDJ-3000, CDJ-2000NXS2, CDJ-2000NXS, CDJ-2000, CDJ-900NXS, CDJ-900, CDJ-850, CDJ-400, CDJ-350)
- Validates: format, sample rate, bit depth, bitrate, channels, file size
- Matrix view showing compatibility across all models at a glance
- Detailed error and warning messages per file–model pair
- CLI `--json` output for scripting

### ☰ Playlist Backup
- Parse **M3U8, M3U, and TXT** playlist formats
- Smart track finding: absolute paths → exact filename match → partial match → extension-agnostic search
- Organize by playlist (separate folders) or flat structure
- Skip duplicates, log missing tracks

### ⇄ Audio Converter
- Convert audio to CDJ-compatible formats with flexible target specification:
  - **Match CDJ model** — auto-derive optimal format from model specs
  - **Match reference file** — clone the format of a file you already like
  - **Preset** — Club Standard (WAV 44.1 kHz/16-bit), High Quality (MP3 320 kbps), Hi-Res (FLAC 96 kHz/24-bit)
  - **Custom** — pick format, sample rate, bit depth, bitrate manually
- **`--prefer-lossless`** — avoid lossy encoding whenever possible:
  - If the selected target format is lossy (MP3, AAC, M4A), the output is automatically overridden to **FLAC**, which is lossless and natively supported on modern CDJ models (CDJ-2000NXS2, CDJ-3000).
  - Source sample rate and bit depth are preserved so no information is discarded beyond what was already lost in the original encode.
  - For lossy source files (e.g. MP3 → FLAC), converting to FLAC **cannot restore** quality that was already discarded, but it **prevents further degradation** from an additional lossy encode.
  - When reducing bit depth to 16-bit (WAV/AIFF), triangular dithering is applied automatically to minimise quantisation noise.
  - Lossless targets (WAV, AIFF, FLAC) are never changed by this flag — it only affects lossy targets.
- Skip already-compatible files, dry-run mode, real-time progress tracking

---

## Installation

### Option 1: Download a Standalone Build (Recommended)

Download pre-built binaries from the [Releases page](../../releases). These include bundled FFmpeg and do **not** require a separate FFmpeg or Python installation.

| Platform | Architecture | File |
|----------|-------------|------|
| macOS | Apple Silicon (M1/M2/M3) | `CDJAudioToolkit-macos-arm64.dmg` |
| macOS | Intel | `CDJAudioToolkit-macos-x86_64.dmg` |
| Windows | x86_64 | `CDJAudioToolkit-windows-x86_64.zip` |
| Linux | x86_64 | `cdj-audio-toolkit-linux-x86_64.AppImage` |

**macOS:** Open the `.dmg` and drag `CDJAudioToolkit.app` to `/Applications`.

> If macOS blocks the app, run:
> ```bash
> xattr -dr com.apple.quarantine /Applications/CDJAudioToolkit.app
> ```

**Windows:** Extract the `.zip` and run `CDJAudioToolkit.exe`.

**Linux:** Make the AppImage executable and run:
```bash
chmod +x cdj-audio-toolkit-linux-x86_64.AppImage
./cdj-audio-toolkit-linux-x86_64.AppImage
```

### Option 2: Install from Source

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python 3.10+** | 3.10, 3.11, 3.12 supported |
| **FFmpeg** | Required for audio analysis and conversion |

Install FFmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg

# Windows (Chocolate)
choco install ffmpeg
```

#### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/cdj-audio-toolkit.git
cd cdj-audio-toolkit

# 2. (Optional but recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install the package (with dev and GUI dependencies)
pip install -e ".[dev]"
pip install -e ".[gui-test]"

# 4. Verify installation
python -m src.cli --help
python -m pytest tests/ -v
```

---

## Usage

### GUI Application

```bash
python run_gui.py
```

**Using the GUI:**

1. **Check tab** — Add audio files via the file list or drag-and-drop. Select a CDJ model (or "All Models"). Click **Check Compatibility** to see the results matrix.
2. **Backup tab** — Enter the path to a playlist file (`.m3u8`/`.m3u`/`.txt`), your music directory, and a backup destination. Optionally organize by playlist and skip existing files. Click **Start Backup**.
3. **Convert tab** — Add files or playlists. Choose a target format (CDJ model, reference file, preset, or custom). Set the output directory. Click **Start Conversion**.

### Command-Line Interface

The CLI provides the same functionality as the GUI with `check`, `backup`, and `convert` subcommands.

```bash
cdj-tool --help
cdj-tool <subcommand> --help
```

#### Check Compatibility

```bash
# Check a single file against all CDJ models
cdj-tool check track.flac

# Check against a specific model
cdj-tool check track.mp3 --model cdj-3000

# Check an entire directory recursively
cdj-tool check ./music --recursive

# Output as JSON (for scripting)
cdj-tool check track.flac --json
```

#### Backup Playlist Tracks

```bash
# Backup a single playlist
cdj-tool backup myset.m3u8

# Backup with custom directories
cdj-tool backup myset.m3u8 --music-dir /Volumes/DJ/music --output-dir /Volumes/USB/backup

# Organize by playlist (creates subfolders)
cdj-tool backup myset.m3u8 --organize

# Backup all playlists in a directory
cdj-tool backup ./playlists/ --organize --skip-existing --log-missing missing.txt
```

#### Convert Audio

```bash
# Convert to CDJ-3000 optimal format
cdj-tool convert track.flac --model cdj-3000

# Match format of a reference file
cdj-tool convert track.flac --reference track_i_like.wav

# Use a built-in preset
cdj-tool convert track.wav --preset club
cdj-tool convert track.wav --preset high-quality
cdj-tool convert track.wav --preset hires

# Convert all tracks in a playlist
cdj-tool convert myset.m3u8 --preset club --music-dir ./music

# Convert an entire directory
cdj-tool convert ./music --format flac --sample-rate 96000 --bit-depth 24

# Prefer lossless output — avoids lossy encoding even if the preset/target is lossy
# (e.g. --preset high_quality would normally produce MP3; with this flag it
# produces FLAC instead, preventing generational quality loss)
cdj-tool convert ./music --preset high_quality --prefer-lossless

# Dry run — see what would be converted
cdj-tool convert ./music --model cdj-3000 --dry-run

# Skip files already matching the target
cdj-tool convert ./music --preset club --skip-compatible

# Output as JSON
cdj-tool convert track.wav --preset club --json
```

---

## CDJ Model Specifications

| Model | Formats | Sample Rates | Bit Depths | Rekordbox | SD Card |
|-------|---------|-------------|------------|-----------|---------|
| CDJ-3000 | MP3, AAC, WAV, AIFF, FLAC, ALAC | 44.1 – 192 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000NXS2 | MP3, AAC, WAV, AIFF, FLAC, ALAC | 44.1 – 96 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000NXS | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✓ |
| CDJ-2000 | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✓ |
| CDJ-900NXS | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-900 | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-850 | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16, 24 | ✓ | ✗ |
| CDJ-400 | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16 | ✗ | ✗ |
| CDJ-350 | MP3, AAC, WAV, AIFF | 44.1, 48 kHz | 16 | ✓ | ✗ |

## Recommended Conversion Presets

| Preset | Format | Sample Rate | Bit Depth | Bitrate | Use Case |
|--------|--------|-------------|-----------|---------|----------|
| Club Standard | WAV | 44.1 kHz | 16-bit | — | Maximum club compatibility |
| High Quality | MP3 | 44.1 kHz | — | 320 kbps | Small file size, good quality |
| Hi-Res | FLAC | 96 kHz | 24-bit | — | Audiophile, CDJ-3000 only |

---

## Development

### Project Structure

```
cdj-audio-toolkit/
├── src/                    # Core engine (CLI-compatible)
│   ├── config.py           # CDJ model specs, presets, constants
│   ├── metadata.py         # ffprobe wrapper, AudioMetadata dataclass
│   ├── compatibility.py    # Compatibility checking engine
│   ├── backup.py           # Playlist parsing and backup engine
│   ├── converter.py        # FFmpeg conversion engine
│   ├── cli.py              # argparse CLI (check / backup / convert)
│   └── utils.py            # FFmpeg resolution, formatting utilities
├── gui/                    # PySide6 desktop application
│   ├── app.py              # Main window with tabs, drag-and-drop
│   ├── theme.py            # Dark QSS theme
│   ├── tabs/
│   │   ├── check_tab.py    # Compatibility matrix tab
│   │   ├── backup_tab.py   # Playlist backup tab
│   │   └── convert_tab.py  # Audio conversion tab
│   └── components/         # Reusable widgets (file selector, log viewer, etc.)
├── build/
│   ├── bundle_ffmpeg.py    # Download/copy FFmpeg binaries for bundling
│   └── build.spec          # PyInstaller build configuration
├── tests/                  # Unit tests (85+ tests)
├── ffmpeg/                 # Bundled FFmpeg binaries (per-platform)
├── pyproject.toml          # Project metadata and dependencies
└── run_gui.py              # GUI launcher script
```

### Running the Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov=gui

# Specific module
pytest tests/test_compatibility.py -v
```

### Architecture Overview

The core engine (`src/`) is completely independent of the GUI. This separation allows the same code to power both the CLI and the desktop application.

```
┌───────────────────────────────────────┐
│           Presentation Layer          │
│  ┌────────────┐   ┌────────────────┐  │
│  │  CLI       │   │  GUI (PySide6) │  │
│  │ (argparse) │   │  (3 tabs)      │  │
│  └─────┬──────┘   └──────┬─────────┘  │
└────────┼─────────────────┼────────────┘
         │                 │
         ▼                 ▼
┌───────────────────────────────────────┐
│            Core Engine                │
│  ┌───────────┐ ┌──────────┐ ┌───────┐│
│  │compatibil.│ │  backup  │ │convert││
│  └─────┬─────┘ └────┬─────┘ └───┬───┘│
│        │            │           │     │
│  ┌─────┴────────────┴───────────┴───┐ │
│  │         metadata.py              │ │
│  │         (ffprobe wrapper)        │ │
│  └──────────────────────────────────┘ │
└───────────────────────────────────────┘
         │                 │
         ▼                 ▼
   ┌──────────┐     ┌──────────┐
   │  ffprobe │     │  ffmpeg  │
   └──────────┘     └──────────┘
```

### Building Standalone Binaries

```bash
# 1. Bundle FFmpeg from your system PATH
python build/bundle_ffmpeg.py --from-system

# 2. Install PyInstaller
pip install pyinstaller

# 3. Build the standalone app
pyinstaller build/build.spec

# 4. Output
#    macOS: dist/CDJAudioToolkit.app/
#    Linux: dist/cdj-audio-toolkit/
#    Windows: dist/CDJAudioToolkit.exe
```

### CI/CD Pipeline

This project uses GitHub Actions to build and distribute binaries for all platforms.

| Job | Runner | Output |
|-----|--------|--------|
| `test` | `ubuntu-latest` | pytest results (gate) |
| `build-macos-arm64` | `macos-14` (Apple Silicon) | `.dmg` |
| `build-macos-x86_64` | `macos-13` (Intel) | `.dmg` |
| `build-windows` | `windows-latest` | `.zip` |
| `build-linux` | `ubuntu-22.04` | `.AppImage` (+ `.tar.gz` fallback) |
| `release` | `ubuntu-latest` | GitHub Release (draft) |

**Trigger a release:**

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow creates a **draft** GitHub Release with all platform artifacts attached. Review and publish from the Releases page.

---

## Contributing

Contributions are welcome! Here's how you can help:

### Setting Up a Development Environment

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/cdj-audio-toolkit.git
cd cdj-audio-toolkit

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install with dev dependencies
pip install -e ".[dev]"

# 4. Verify everything works
pytest tests/ -v
python run_gui.py
```

### Making Changes

1. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Write tests** for new functionality:
   - Place tests in `tests/`
   - Follow the existing naming conventions (`TestClassName`, `test_method_name`)
   - Use `tempfile.mkdtemp()` for temp directories (avoid `tmp_path` fixture due to plugin conflicts)

3. **Ensure all tests pass**:
   ```bash
   pytest tests/ -v
   ```

4. **Follow the coding style**:
   - Type hints on all public functions and methods
   - Docstrings for modules, classes, and public functions
   - Frozen dataclasses where mutation is not needed
   - Module-level imports at the top, no wildcard imports

5. **Commit with clear messages**:
   ```bash
   git add <files>
   git commit -m "Add feature: brief description of what changed"
   ```

### Pull Request Guidelines

- **One feature per PR** — keep changes focused and easy to review
- **Include tests** — new features should have corresponding tests
- **Update the README** if you add or change user-facing behavior
- **Describe the why** — explain the motivation and any trade-offs in the PR description

### Reporting Issues

When filing a bug report, please include:
- **Platform**: OS and architecture (e.g., "macOS 14.5, Apple Silicon M2")
- **Python version**: `python --version`
- **FFmpeg version**: `ffmpeg -version | head -1`
- **Steps to reproduce** the issue
- **Expected vs. actual behavior**
- **Error messages** or screenshots (for GUI issues)

### Good First Issues

Look for issues labeled [`good first issue`](../../labels/good%20first%20issue) — these are beginner-friendly tasks to help you get familiar with the codebase.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- **FFmpeg** — The backbone of all audio processing in this project
- **Pioneer DJ** — For the CDJ hardware specifications used as reference data
- **PySide6 / Qt** — For the cross-platform GUI framework
- **PyInstaller** — For standalone application packaging
