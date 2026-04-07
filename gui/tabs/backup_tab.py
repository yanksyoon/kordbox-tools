"""Backup tab — playlist track backup."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.backup import parse_playlist, resolve_tracks, backup_tracks
from src.config import PLAYLIST_EXTENSIONS
from gui.components import (
    DirSelector,
    FileSelector,
    LogViewer,
    ProgressWidget,
)


class _BackupWorker(QThread):
    """Background worker for playlist backup."""
    progress = Signal(int, int, str)
    log_line = Signal(str, str)   # type: "ok"/"err"/"warn"/"info", message
    finished = Signal(object)     # BackupReport

    def __init__(
        self,
        playlists: list[str],
        music_dirs: list[str],
        output_dir: str,
        organize: bool,
        skip_existing: bool,
        log_missing: bool,
    ):
        super().__init__()
        self.playlists = playlists
        self.music_dirs = music_dirs
        self.output_dir = output_dir
        self.organize = organize
        self.skip_existing = skip_existing
        self.log_missing = log_missing

    def run(self):
        from src.backup import BackupReport
        combined_report = BackupReport(output_dir=self.output_dir)

        for pl_file in self.playlists:
            pl_name = Path(pl_file).stem
            self.log_line.emit("info", f"--- Playlist: {pl_name} ---")

            raw = parse_playlist(pl_file)
            self.log_line.emit("info", f"  Found {len(raw)} track(s) in playlist")
            tracks = resolve_tracks(raw, self.music_dirs)

            def _on_progress(i, total, name):
                self.progress.emit(i, total, name)

            report = backup_tracks(
                tracks=tracks,
                output_dir=self.output_dir,
                organize_by_playlist=self.organize,
                skip_existing=self.skip_existing,
                playlist_name=pl_name,
                log_missing=self.log_missing,
                on_progress=_on_progress,
            )

            combined_report.copied += report.copied
            combined_report.skipped += report.skipped
            combined_report.missing += report.missing
            combined_report.failed += report.failed

            self.log_line.emit("info", f"  Copied: {report.copied}, Skipped: {report.skipped}, Missing: {report.missing}")

            for t in tracks:
                if t.exists:
                    self.log_line.emit("ok", f"  Found: {Path(t.original_path).name}")
                else:
                    self.log_line.emit("warn", f"  Missing: {t.original_path}")

        self.finished.emit(combined_report)


class BackupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[_BackupWorker] = None

        layout = QVBoxLayout(self)

        # ── Input section ──
        self.playlist_selector = FileSelector(
            label="Playlist:",
            name_filter="Playlists (*.m3u8 *.m3u *.txt);;All Files (*)",
        )
        layout.addWidget(self.playlist_selector)

        self.music_dir_selector = DirSelector(label="Music Directory:")
        self.music_dir_selector.set_text("./music")
        layout.addWidget(self.music_dir_selector)

        self.output_selector = DirSelector(label="Backup Directory:")
        self.output_selector.set_text("./backup")
        layout.addWidget(self.output_selector)

        # ── Options ──
        opts = QHBoxLayout()
        self.chk_organize = QCheckBox("Organize by playlist")
        self.chk_skip = QCheckBox("Skip existing files")
        self.chk_skip.setChecked(True)
        opts.addWidget(self.chk_organize)
        opts.addWidget(self.chk_skip)
        opts.addStretch()
        layout.addLayout(opts)

        # ── Action button ──
        action_layout = QHBoxLayout()
        self.backup_btn = QPushButton("▶ Start Backup")
        self.backup_btn.clicked.connect(self._start_backup)
        action_layout.addWidget(self.backup_btn)
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

    def _start_backup(self):
        playlist_path = self.playlist_selector.text()
        if not playlist_path or not os.path.exists(playlist_path):
            self.log.append_error("Playlist file not found")
            return

        # Resolve to list of playlist files
        if os.path.isfile(playlist_path):
            playlists = [playlist_path]
        else:
            playlists = [
                str(p) for p in Path(playlist_path).iterdir()
                if p.is_file() and p.suffix.lower().lstrip(".") in PLAYLIST_EXTENSIONS
            ]

        if not playlists:
            self.log.append_error("No playlist files found")
            return

        music_dir = self.music_dir_selector.text()
        output_dir = self.output_selector.text()

        self.log.clear_log()
        self.progress.reset()
        self.backup_btn.setEnabled(False)

        self._worker = _BackupWorker(
            playlists=playlists,
            music_dirs=[music_dir],
            output_dir=output_dir,
            organize=self.chk_organize.isChecked(),
            skip_existing=self.chk_skip.isChecked(),
            log_missing=True,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        self.progress.set_progress(current + 1, total)
        self.progress.set_status(f"Backing up {name}")

    def _on_log(self, type_: str, message: str):
        if type_ == "ok":
            self.log.append_success(message)
        elif type_ == "err":
            self.log.append_error(message)
        elif type_ == "warn":
            self.log.append_warning(message)
        else:
            self.log.append_info(message)

    def _on_finished(self, report):
        self.backup_btn.setEnabled(True)
        self.progress.set_status(
            f"Done — Copied: {report.copied}, Skipped: {report.skipped}, "
            f"Missing: {report.missing}"
        )
        self.log.append_line("")
        self.log.append_info(f"Summary: {report.copied} copied, {report.skipped} skipped, {report.missing} missing")
