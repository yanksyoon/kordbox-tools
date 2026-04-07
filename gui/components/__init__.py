"""Reusable GUI components — file selector, model selector, progress, log viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QComboBox,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.config import CDJ_MODELS
from src.utils import get_display_model_name


class FileSelector(QWidget):
    """A line edit with a browse button."""

    def __init__(
        self,
        label: str = "Path:",
        file_mode: QFileDialog.FileMode = QFileDialog.AnyFile,
        name_filter: str = "All Files (*)",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._file_mode = file_mode
        self._name_filter = name_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        self.line_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.setProperty("role", "secondary")

        layout.addWidget(lbl)
        layout.addWidget(self.line_edit)
        layout.addWidget(browse_btn)

        browse_btn.clicked.connect(self._browse)

    def _browse(self):
        if self._file_mode == QFileDialog.Directory:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", filter=self._name_filter
            )
        if path:
            self.line_edit.setText(path)

    def text(self) -> str:
        return self.line_edit.text()

    def set_text(self, text: str):
        self.line_edit.setText(text)


class DirSelector(FileSelector):
    """File selector configured for directories."""

    def __init__(self, label: str = "Directory:", parent=None):
        super().__init__(
            label=label,
            file_mode=QFileDialog.Directory,
            parent=parent,
        )


class FileListWidget(QWidget):
    """A QListWidget with add/remove buttons."""

    def __init__(
        self,
        name_filter: str = "Audio Files (*.mp3 *.wav *.aiff *.flac *.aac *.m4a *.alac);;All Files (*)",
        parent=None,
    ):
        super().__init__(parent)
        self._name_filter = name_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        btn_layout = QVBoxLayout()

        add_btn = QPushButton("Add")
        add_btn.setProperty("role", "secondary")
        add_btn.clicked.connect(self._add_files)

        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("role", "secondary")
        remove_btn.clicked.connect(self._remove_selected)

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("role", "secondary")
        clear_btn.clicked.connect(self.list_widget.clear)

        btn_layout.addStretch()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()

        layout.addWidget(self.list_widget)
        layout.addLayout(btn_layout)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Files", filter=self._name_filter
        )
        for f in files:
            self.list_widget.addItem(f)

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

    def file_paths(self) -> list[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def add_path(self, path: str):
        self.list_widget.addItem(path)

    def count(self) -> int:
        return self.list_widget.count()


class ModelSelector(QWidget):
    """Dropdown to select a CDJ model, with 'All Models' option."""

    def __init__(self, parent=None, include_all: bool = True):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox()
        if include_all:
            self.combo.addItem("All Models")
        for key in CDJ_MODELS:
            self.combo.addItem(get_display_model_name(key), userData=key)
        layout.addWidget(self.combo)

    def selected_key(self) -> Optional[str]:
        """Return the internal model key, or None if 'All Models' is selected."""
        idx = self.combo.currentIndex()
        if idx == 0 and self.combo.itemText(0) == "All Models":
            return None
        return self.combo.itemData(idx)

    def selected_display(self) -> str:
        return self.combo.currentText()


class LogViewer(QTextEdit):
    """Read-only text edit for log output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)

    def append_line(self, text: str):
        self.append(text)

    def append_success(self, text: str):
        self.append(f"✓ {text}")

    def append_error(self, text: str):
        self.append(f"✗ {text}")

    def append_warning(self, text: str):
        self.append(f"⚠ {text}")

    def append_info(self, text: str):
        self.append(f"  {text}")

    def clear_log(self):
        self.clear()


class ProgressWidget(QWidget):
    """Progress bar with status label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_progress(self, current: int, total: int):
        if total == 0:
            pct = 0
        else:
            pct = int(current / total * 100)
        self.progress_bar.setValue(pct)
        self.set_status(f"{current}/{total}")

    def reset(self):
        self.progress_bar.setValue(0)
        self.set_status("Ready")
