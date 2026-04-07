"""Main GUI application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStatusBar,
    QTabWidget,
)

from gui.theme import apply_theme
from gui.tabs.check_tab import CheckTab
from gui.tabs.backup_tab import BackupTab
from gui.tabs.convert_tab import ConvertTab


class MainWindow(QMainWindow):
    """Main application window with tabs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CDJ Audio Toolkit")
        self.setMinimumSize(1100, 800)
        self.setAcceptDrops(True)

        # ── Tab widget ──
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.check_tab = CheckTab()
        self.backup_tab = BackupTab()
        self.convert_tab = ConvertTab()

        self.tabs.addTab(self.check_tab, "◉ Check")
        self.tabs.addTab(self.backup_tab, "☰ Backup")
        self.tabs.addTab(self.convert_tab, "⇄ Convert")

        # ── Status bar ──
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag events with file URIs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle dropped files — add to the current tab's file list."""
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).exists():
                files.append(path)

        if not files:
            return

        current = self.tabs.currentIndex()
        if current == 0:  # Check tab
            for f in files:
                self.check_tab.file_list.add_path(f)
        elif current == 2:  # Convert tab
            for f in files:
                self.convert_tab.file_list.add_path(f)
        # Backup tab uses a single file selector, not a list

        self.status.showMessage(f"Added {len(files)} file(s)")


def run_gui() -> None:
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    apply_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
