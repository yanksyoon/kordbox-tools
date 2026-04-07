"""Check tab — compatibility matrix."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.compatibility import check_all_models, check_compatibility
from src.config import CDJ_MODELS
from src.utils import get_display_model_name
from gui.components import FileListWidget, ModelSelector, LogViewer, ProgressWidget


class _CheckWorker(QThread):
    """Background worker for compatibility checking."""
    file_done = Signal(str, dict)   # filepath -> {model: result_dict}
    progress = Signal(int, int, str)
    finished = Signal()

    def __init__(self, files: list[str], model_key: Optional[str]):
        super().__init__()
        self.files = files
        self.model_key = model_key

    def run(self):
        for i, filepath in enumerate(self.files):
            self.progress.emit(i, len(self.files), Path(filepath).name)
            if self.model_key:
                result = check_compatibility(filepath, self.model_key)
                self.file_done.emit(filepath, {result.model: _result_dict(result)})
            else:
                results = check_all_models(filepath)
                self.file_done.emit(filepath, {
                    k: _result_dict(v) for k, v in results.items()
                })
        self.finished.emit()


def _result_dict(r) -> dict:
    return {
        "compatible": r.compatible,
        "errors": r.errors,
        "warnings": r.warnings,
        "notes": r.notes,
    }


class CheckTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[_CheckWorker] = None
        self._results: dict[str, dict] = {}  # filepath -> {model: result}

        layout = QVBoxLayout(self)

        # ── Input section ──
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)

        # Controls row
        controls = QHBoxLayout()
        self.model_selector = ModelSelector(include_all=True)
        controls.addWidget(self.model_selector)

        self.check_btn = QPushButton("▶ Check Compatibility")
        self.check_btn.clicked.connect(self._start_check)
        controls.addWidget(self.check_btn)
        layout.addLayout(controls)

        # ── Progress ──
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        # ── Results table ──
        table_group = QGroupBox("Results")
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellClicked.connect(self._on_cell_clicked)
        table_layout.addWidget(self.table)
        layout.addWidget(table_group)

        # ── Detail log ──
        log_group = QGroupBox("Detail")
        log_layout = QVBoxLayout(log_group)
        self.log = LogViewer()
        log_layout.addWidget(self.log)
        layout.addWidget(log_group)

    def _start_check(self):
        files = self.file_list.file_paths()
        if not files:
            return

        model_key = self.model_selector.selected_key()
        self._results.clear()
        self.table.clear()
        self.log.clear_log()

        self._worker = _CheckWorker(files, model_key)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished.connect(self._on_finished)
        self.check_btn.setEnabled(False)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        self.progress.set_progress(current + 1, total)
        self.progress.set_status(f"Checking {name}")

    def _on_file_done(self, filepath: str, model_results: dict):
        self._results[filepath] = model_results

        # Build/update table
        model_names = list(next(iter(model_results.keys()), None) for _ in [1])
        if not model_names[0]:
            return

        # Set up columns: File + all models
        all_models = sorted(model_results.keys(), key=lambda m: list(CDJ_MODELS.keys()).index(
            next(k for k, v in CDJ_MODELS.items() if get_display_model_name(k) == m)
        ) if any(get_display_model_name(k) == m for k in CDJ_MODELS) else 99)

        self.table.setColumnCount(len(all_models) + 1)
        self.table.setHorizontalHeaderLabels(["File"] + all_models)

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(Path(filepath).name))

        for col, model_name in enumerate(all_models, 1):
            r = model_results.get(model_name, {})
            compatible = r.get("compatible", False)
            item = QTableWidgetItem("✓" if compatible else "✗")
            if compatible:
                item.setToolTip("\n".join(r.get("notes", [])))
            else:
                item.setToolTip("\n".join(r.get("errors", [])))
            self.table.setItem(row, col, item)

    def _on_finished(self):
        self.check_btn.setEnabled(True)
        self.progress.set_status("Done")

    def _on_cell_clicked(self, row: int, col: int):
        if col == 0:
            return
        filepath = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        model_name = self.table.horizontalHeaderItem(col).text() if self.table.horizontalHeaderItem(col) else ""

        # Find the full filepath
        full_path = None
        for fp in self._results:
            if Path(fp).name == filepath:
                full_path = fp
                break
        if full_path is None:
            return

        self.log.clear_log()
        r = self._results.get(full_path, {}).get(model_name, {})
        self.log.append_line(f"File: {filepath}  |  Model: {model_name}")
        self.log.append_line("")
        for e in r.get("errors", []):
            self.log.append_error(e)
        for w in r.get("warnings", []):
            self.log.append_warning(w)
        for n in r.get("notes", []):
            self.log.append_info(n)
