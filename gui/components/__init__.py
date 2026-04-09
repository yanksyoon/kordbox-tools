"""Reusable GUI components — file selector, model selector, progress, log viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Set, List

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
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

from src.config import CDJ_MODELS
from src.utils import get_display_model_name


class _ModelSelectionDialog(QDialog):
    """Dialog for selecting multiple CDJ models."""
    
    def __init__(self, current_selection: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select CDJ Models")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        layout.addWidget(QLabel("Select the CDJ models to check:"))
        
        # List widget with checkboxes
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(300)
        
        # Add all models with checkboxes
        self._model_keys = list(CDJ_MODELS.keys())
        for key in self._model_keys:
            item = QListWidgetItem(get_display_model_name(key))
            item.setData(1000, key)
            item.setCheckState(Qt.Checked if key in current_selection else Qt.Unchecked)
            self.list_widget.addItem(item)
        
        # Connect item click to toggle checkbox
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self._reset_selection)
        
        layout.addWidget(button_box)
        
        self.resize(300, 400)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Toggle checkbox when item is clicked anywhere."""
        current_state = item.checkState()
        new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
        item.setCheckState(new_state)
    
    def _reset_selection(self):
        """Reset all checkboxes to checked."""
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
    
    def selected_keys(self) -> List[str]:
        """Get selected model keys."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(1000))
        return sorted(selected)


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

    def _browse(self) -> None:
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

    def set_text(self, text: str) -> None:
        self.line_edit.setText(text)


class DirSelector(FileSelector):
    """File selector configured for directories."""

    def __init__(self, label: str = "Directory:", parent: Optional[QWidget] = None) -> None:
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
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._name_filter: str = name_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget: QListWidget = QListWidget()
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

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Files", filter=self._name_filter
        )
        for f in files:
            self.list_widget.addItem(f)

    def _remove_selected(self) -> None:
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

    def file_paths(self) -> list[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def add_path(self, path: str) -> None:
        self.list_widget.addItem(path)

    def count(self) -> int:
        return self.list_widget.count()


class ModelSelector(QWidget):
    """Dropdown to select a CDJ model, with 'All Models' option."""

    def __init__(self, parent: Optional[QWidget] = None, include_all: bool = True) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo: QComboBox = QComboBox()
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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)

    def append_line(self, text: str) -> None:
        self.append(text)

    def append_success(self, text: str) -> None:
        self.append(f"✓ {text}")

    def append_error(self, text: str) -> None:
        self.append(f"✗ {text}")

    def append_warning(self, text: str) -> None:
        self.append(f"⚠ {text}")

    def append_info(self, text: str) -> None:
        self.append(f"  {text}")

    def clear_log(self) -> None:
        self.clear()


class ProgressWidget(QWidget):
    """Progress bar with status label."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        self.status_label: QLabel = QLabel("Ready")
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, current: int, total: int) -> None:
        if total == 0:
            pct = 0
        else:
            pct = int(current / total * 100)
        self.progress_bar.setValue(pct)
        self.set_status(f"{current}/{total}")

    def reset(self) -> None:
        self.progress_bar.setValue(0)
        self.set_status("Ready")

class MultiModelSelector(QWidget):
    """Multi-select widget for CDJ models using a dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label showing current selection
        self.display_label: QLabel = QLabel("All Models")
        self.display_label.setStyleSheet("border: 1px solid #ccc; padding: 2px 4px; border-radius: 3px;")
        self.display_label.mousePressEvent = self._show_selection_dialog
        layout.addWidget(self.display_label)

        # Select button
        select_btn = QPushButton("Select Models")
        select_btn.setProperty("role", "secondary")
        select_btn.clicked.connect(self._show_selection_dialog)
        layout.addWidget(select_btn)

        # Initialize selection
        self._model_keys: List[str] = list(CDJ_MODELS.keys())
        self._selected_keys: Set[str] = set(self._model_keys)
        self._update_display()

    def _show_selection_dialog(self, event=None) -> None:
        """Show the model selection dialog."""
        dialog = _ModelSelectionDialog(self._selected_keys, self)
        if dialog.exec() == QDialog.Accepted:
            self._selected_keys = set(dialog.selected_keys())
            self._update_display()

    def _update_display(self) -> None:
        """Update the display label with current selections."""
        if len(self._selected_keys) == len(self._model_keys):
            text = "All Models"
        elif len(self._selected_keys) == 0:
            text = "No Models"
        elif len(self._selected_keys) == 1:
            key = list(self._selected_keys)[0]
            text = get_display_model_name(key)
        else:
            count = len(self._selected_keys)
            text = f"{count} Models"
        
        self.display_label.setText(text)
        
        # Update tooltip with full list
        if self._selected_keys:
            names = [get_display_model_name(k) for k in sorted(self._selected_keys)]
            self.display_label.setToolTip(", ".join(names))
        else:
            self.display_label.setToolTip("")

    def selected_keys(self) -> List[str]:
        """Return sorted list of selected model keys."""
        return sorted(list(self._selected_keys))

    def selected_displays(self) -> List[str]:
        """Return list of selected model display names."""
        return [get_display_model_name(k) for k in sorted(self._selected_keys)]

    def set_selected(self, keys: List[str]) -> None:
        """Set selected models by their keys."""
        self._selected_keys = set(keys)
        self._update_display()

    def select_all(self) -> None:
        """Select all models."""
        self.set_selected(self._model_keys)

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.set_selected([])