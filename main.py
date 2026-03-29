"""
main.py — Application entry point for GST Reconciliation Desktop App.

Usage:
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

import config
from database.client_master import init_db
from ui.main_window import MainWindow


def main() -> None:
    """Initialise the database, create the Qt application, and show the main window."""
    # Initialise database (creates tables if they don't exist)
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_TITLE)
    app.setApplicationVersion(config.APP_VERSION)

    # Apply a clean application-wide stylesheet
    app.setStyleSheet(
        """
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        QTableWidget {
            gridline-color: #D0DDEE;
        }
        QTableWidget::item:selected {
            background-color: #CCE0F5;
            color: #1B3A6B;
        }
        QHeaderView::section {
            background-color: #2E75B6;
            color: white;
            padding: 6px;
            font-weight: bold;
            border: none;
        }
        QScrollBar:vertical {
            width: 10px;
            background: #F0F0F0;
        }
        QScrollBar::handle:vertical {
            background: #AAAAAA;
            border-radius: 5px;
        }
        """
    )

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
