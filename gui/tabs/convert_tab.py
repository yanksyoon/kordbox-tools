"""Convert tab — audio conversion with target format selection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
    QGridLayout,
    QPushButton,
)

from src.config import CONVERSION_PRESETS, PLAYLIST_EXTENSIONS, AUDIO_EXTENSIONS
from src.converter import (
    ConversionTarget,
    convert_batch,
    target_from_model,
    target_from_preset,
    target_from_reference,
    scan_audio_files,
)
from src.backup import parse_playlist, resolve_tracks
from src.utils import format_size
from gui.components import (
    DirSelector,
    FileListWidget,
    FileSelector,
    LogViewer,
    ModelSelector,
    ProgressWidget,
)


class _ConvertWorker(QThread):
    """Background worker for audio conversion."""
    progress = Signal(int, int, str)
    log_line = Signal(str, str)
    finished = Signal(object)

    def __init__(
        self,
        files: list[str],
        output_dir: str,
        target: ConversionTarget,
        skip_compatible: bool,
        overwrite: bool,
        prefer_lossless: bool = False,
    ):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target = target
        self.skip_compatible = skip_compatible
        self.overwrite = overwrite
        self.prefer_lossless = prefer_lossless

    def run(self):
        report = convert_batch(
            input_files=self.files,
            output_dir=self.output_dir,
            target=self.target,
            skip_compatible=self.skip_compatible,
            overwrite=self.overwrite,
            prefer_lossless=self.prefer_lossless,
            on_progress=lambda i, total, name: self.progress.emit(i, total, name),
        )
        self.finished.emit(report)


class ConvertTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[_ConvertWorker] = None

        layout = QVBoxLayout(self)

        # ── Input ──
        self.file_list = FileListWidget(
            name_filter="Audio Files (*.mp3 *.wav *.aiff *.flac *.aac *.m4a *.alac *.ogg *.wma *.opus *.m3u8 *.m3u *.txt);;All Files (*)"
        )
        layout.addWidget(self.file_list)

        # ── Target format ──
        target_group = QGroupBox("Target Format")
        target_layout = QVBoxLayout(target_group)

        self.target_group_btn = QButtonGroup(self)

        # Radio: Match CDJ model
        self.radio_model = QRadioButton("Match CDJ model:")
        self.target_group_btn.addButton(self.radio_model, 0)
        model_row = QHBoxLayout()
        model_row.addWidget(self.radio_model)
        self.model_selector = ModelSelector(include_all=False)
        self.model_selector.combo.setCurrentText("CDJ-3000")
        model_row.addWidget(self.model_selector)
        model_row.addStretch()
        target_layout.addLayout(model_row)

        # Radio: Match reference file
        self.radio_ref = QRadioButton("Match reference file:")
        self.target_group_btn.addButton(self.radio_ref, 1)
        ref_row = QHBoxLayout()
        ref_row.addWidget(self.radio_ref)
        self.ref_selector = FileSelector(
            label="",
            name_filter="Audio Files (*.mp3 *.wav *.aiff *.flac *.aac *.m4a *.alac);;All Files (*)",
        )
        ref_row.addWidget(self.ref_selector)
        target_layout.addLayout(ref_row)

        # Radio: Use preset
        self.radio_preset = QRadioButton("Use preset:")
        self.target_group_btn.addButton(self.radio_preset, 2)
        self.radio_preset.setChecked(True)  # Default
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.radio_preset)
        self.preset_combo = QComboBox()
        for key, preset in CONVERSION_PRESETS.items():
            label = key.replace("_", " ").title()
            detail = f"{preset.format.upper()}"
            if preset.sample_rate:
                detail += f" {preset.sample_rate}Hz"
            if preset.bit_depth:
                detail += f" {preset.bit_depth}-bit"
            if preset.bitrate:
                detail += f" {preset.bitrate}"
            self.preset_combo.addItem(f"{label} ({detail})", userData=key)
        preset_row.addWidget(self.preset_combo)
        preset_row.addStretch()
        target_layout.addLayout(preset_row)

        # Radio: Custom
        self.radio_custom = QRadioButton("Custom:")
        self.target_group_btn.addButton(self.radio_custom, 3)
        custom_grid = QGridLayout()
        custom_grid.addWidget(self.radio_custom, 0, 0)
        custom_grid.addWidget(QLabel("Format:"), 0, 1)
        self.custom_format = QComboBox()
        self.custom_format.addItems(["wav", "mp3", "flac", "aiff", "aac"])
        custom_grid.addWidget(self.custom_format, 0, 2)
        custom_grid.addWidget(QLabel("Sample Rate:"), 1, 1)
        self.custom_sr = QComboBox()
        self.custom_sr.addItems(["44100", "48000", "88200", "96000", "176400", "192000"])
        self.custom_sr.setCurrentText("44100")
        custom_grid.addWidget(self.custom_sr, 1, 2)
        custom_grid.addWidget(QLabel("Bit Depth:"), 2, 1)
        self.custom_bd = QComboBox()
        self.custom_bd.addItems(["16", "24"])
        custom_grid.addWidget(self.custom_bd, 2, 2)
        custom_grid.addWidget(QLabel("Bitrate:"), 3, 1)
        self.custom_br = QComboBox()
        self.custom_br.addItems(["128k", "192k", "256k", "320k"])
        self.custom_br.setCurrentText("320k")
        custom_grid.addWidget(self.custom_br, 3, 2)
        target_layout.addLayout(custom_grid)

        layout.addWidget(target_group)

        # ── Output dir ──
        self.output_selector = DirSelector(label="Output Directory:")
        self.output_selector.set_text("./output")
        layout.addWidget(self.output_selector)

        # ── Options ──
        opts = QHBoxLayout()
        self.chk_skip = QCheckBox("Skip compatible")
        self.chk_skip.setChecked(True)
        self.chk_overwrite = QCheckBox("Overwrite existing")
        self.chk_dryrun = QCheckBox("Dry run")
        self.chk_prefer_lossless = QCheckBox("Prefer lossless")
        self.chk_prefer_lossless.setToolTip(
            "Avoid lossy encoding: if the selected target format is lossy (MP3, AAC, M4A), "
            "automatically convert to FLAC instead.\n"
            "Note: converting a lossy source to FLAC cannot restore lost quality, "
            "but prevents further degradation."
        )
        opts.addWidget(self.chk_skip)
        opts.addWidget(self.chk_overwrite)
        opts.addWidget(self.chk_dryrun)
        opts.addWidget(self.chk_prefer_lossless)
        opts.addStretch()
        layout.addLayout(opts)

        # ── Action button ──
        action_layout = QHBoxLayout()
        self.convert_btn = QPushButton("▶ Start Conversion")
        self.convert_btn.clicked.connect(self._start_conversion)
        action_layout.addWidget(self.convert_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # ── Progress ──
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        # ── Log ──
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log = LogViewer()
        log_layout.addWidget(self.log)
        layout.addWidget(log_group)

    def _resolve_target(self) -> ConversionTarget:
        btn_id = self.target_group_btn.checkedId()

        if btn_id == 0:  # Model
            key = self.model_selector.selected_key()
            if key:
                return target_from_model(key)
        elif btn_id == 1:  # Reference
            ref = self.ref_selector.text()
            if ref and os.path.isfile(ref):
                return target_from_reference(ref)
        elif btn_id == 2:  # Preset
            key = self.preset_combo.currentData()
            if key:
                return target_from_preset(key)

        # Custom (default fallback)
        return ConversionTarget(
            format=self.custom_format.currentText(),
            sample_rate=int(self.custom_sr.currentText()),
            bit_depth=int(self.custom_bd.currentText()),
            bitrate=self.custom_br.currentText(),
        )

    def _start_conversion(self):
        files = self.file_list.file_paths()
        if not files:
            self.log.append_error("No input files selected")
            return

        target = self._resolve_target()
        output_dir = self.output_selector.text()

        self.log.clear_log()
        self.progress.reset()

        # Dry run
        if self.chk_dryrun.isChecked():
            self.log.append_info(f"Dry run — would convert {len(files)} file(s)")
            self.log.append_info(f"  Target: {target.format} {target.sample_rate or ''}Hz "
                                 f"{target.bit_depth or ''}-bit {target.bitrate or ''}")
            if self.chk_prefer_lossless.isChecked():
                self.log.append_info(
                    "  [prefer-lossless enabled: lossy targets will be overridden to FLAC]"
                )
            for f in files:
                self.log.append_info(f"  {f}")
            return

        self.convert_btn.setEnabled(False)

        # Resolve playlist files if any
        resolved = _resolve_input(files)

        self._worker = _ConvertWorker(
            files=resolved,
            output_dir=output_dir,
            target=target,
            skip_compatible=self.chk_skip.isChecked(),
            overwrite=self.chk_overwrite.isChecked(),
            prefer_lossless=self.chk_prefer_lossless.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        self.progress.set_progress(current + 1, total)
        self.progress.set_status(f"Converting {name}")

    def _on_finished(self, report):
        self.convert_btn.setEnabled(True)
        self.progress.set_status(
            f"Done — Converted: {report.converted}, Skipped: {report.skipped}, "
            f"Failed: {report.failed}"
        )
        self.log.append_line("")
        for r in report.results:
            name = Path(r.input_path).name
            if r.skipped:
                self.log.append_warning(f"⊘ {name} — {r.skipped_reason}")
            elif r.success:
                inp = format_size(r.input_size) if r.input_size else "?"
                out = format_size(r.output_size) if r.output_size else "?"
                self.log.append_success(f"✓ {name} → {Path(r.output_path).name} ({inp} → {out})")
            else:
                self.log.append_error(f"✗ {name} — {r.error}")
        self.log.append_line("")
        self.log.append_info(
            f"Summary: {report.converted} converted, {report.skipped} skipped, "
            f"{report.failed} failed"
        )


def _resolve_input(paths: list[str]) -> list[str]:
    """Resolve a mix of files, directories, and playlists into audio file list."""
    results: list[str] = []
    for path in paths:
        if os.path.isfile(path):
            ext = Path(path).suffix.lower().lstrip(".")
            if ext in PLAYLIST_EXTENSIONS:
                raw = parse_playlist(path)
                # Try to find files relative to the same dir
                music_dirs = [str(Path(path).parent)]
                resolved = resolve_tracks(raw, music_dirs)
                results.extend(t.found_path for t in resolved if t.found_path)
            elif ext in AUDIO_EXTENSIONS:
                results.append(path)
            # else: skip non-audio single files
        elif os.path.isdir(path):
            results.extend(scan_audio_files(path, recursive=True))
    return results
