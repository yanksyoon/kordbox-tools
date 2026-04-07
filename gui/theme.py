"""GUI theme and styling constants."""

from __future__ import annotations

# Color palette
COLORS = {
    "bg_primary": "#1e1e2e",
    "bg_secondary": "#2a2a3c",
    "bg_tertiary": "#363650",
    "text_primary": "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted": "#6c7086",
    "accent": "#89b4fa",
    "accent_hover": "#74c7ec",
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error": "#f38ba8",
    "border": "#45475a",
    "table_header": "#313244",
    "table_row_alt": "#252538",
    "table_row_hover": "#3a3a52",
}

# Common QSS stylesheets
QSS = f"""
/* Main window */
QMainWindow {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
}}

/* Tab bar */
QTabBar::tab {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    padding: 10px 24px;
    border: none;
    border-bottom: 3px solid transparent;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    border-bottom: 3px solid {COLORS['accent']};
}}
QTabBar::tab:hover {{
    color: {COLORS['text_primary']};
}}

/* Tab widget */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_primary']};
}}

/* Labels */
QLabel {{
    color: {COLORS['text_primary']};
}}

/* Line edits */
QLineEdit {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
}}
QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['accent']};
    color: #1e1e2e;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_muted']};
}}

/* Secondary button */
QPushButton[role="secondary"] {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
}}
QPushButton[role="secondary"]:hover {{
    background-color: {COLORS['border']};
}}

/* Checkboxes */
QCheckBox {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['bg_secondary']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

/* Combo boxes */
QComboBox {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent']};
    selection-color: #1e1e2e;
}}

/* List widget */
QListWidget {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: #1e1e2e;
}}

/* Text edit (log viewer) */
QTextEdit {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}

/* Table widget */
QTableWidget {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QTableWidget::item:alternate {{
    background-color: {COLORS['table_row_alt']};
}}
QHeaderView::section {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text_primary']};
    padding: 6px 10px;
    border: none;
    font-weight: bold;
}}

/* Progress bar */
QProgressBar {{
    background-color: {COLORS['bg_tertiary']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 4px;
}}

/* Group box */
QGroupBox {{
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background-color: {COLORS['bg_tertiary']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}

/* Status bar */
QStatusBar {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
}}
"""


def apply_theme(app) -> None:
    """Apply dark theme to the Qt application."""
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
