"""
ui/main_window.py — PyQt6 main window for GST Reconciliation App.

Layout:
    ┌────────────────────────────────────────────────────────────┐
    │  Sidebar  │               Content Area                     │
    │  ─────────┤                                                 │
    │  Dashboard│   (Stacked pages swap here)                    │
    │  Clients  │                                                 │
    │  Reports  │                                                 │
    └────────────────────────────────────────────────────────────┘
    │  Status Bar                                                 │
    └────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import config
from database import client_master
from ui.dialogs import (
    AddClientDialog,
    EditClientDialog,
    ReportOptionsDialog,
)


# ---------------------------------------------------------------------------
# Palette / style constants
# ---------------------------------------------------------------------------

_SIDEBAR_BG = "#1B3A6B"
_SIDEBAR_BTN_DEFAULT = "#1B3A6B"
_SIDEBAR_BTN_HOVER = "#2E5EA8"
_SIDEBAR_BTN_ACTIVE = "#2E75B6"
_SIDEBAR_TEXT = "#FFFFFF"
_CONTENT_BG = "#F4F6FB"
_ACCENT = "#2E75B6"

_SIDEBAR_STYLE = f"""
    QPushButton {{
        background-color: {_SIDEBAR_BTN_DEFAULT};
        color: {_SIDEBAR_TEXT};
        border: none;
        text-align: left;
        padding: 12px 20px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {_SIDEBAR_BTN_HOVER};
    }}
    QPushButton[active="true"] {{
        background-color: {_SIDEBAR_BTN_ACTIVE};
        font-weight: bold;
    }}
"""

_REPORT_BTN_STYLE = """
    QPushButton {
        background-color: #2E75B6;
        color: white;
        border-radius: 6px;
        padding: 10px 16px;
        font-size: 13px;
        text-align: left;
    }
    QPushButton:hover {
        background-color: #1F5A9C;
    }
    QPushButton:pressed {
        background-color: #144077;
    }
"""


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_TITLE} v{config.APP_VERSION}")
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        # Content area (stacked pages)
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {_CONTENT_BG};")
        root_layout.addWidget(self._stack, stretch=1)

        # Pages
        self._dashboard_page = self._build_dashboard_page()
        self._clients_page = self._build_clients_page()
        self._reports_page = self._build_reports_page()

        self._stack.addWidget(self._dashboard_page)
        self._stack.addWidget(self._clients_page)
        self._stack.addWidget(self._reports_page)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status("Ready")

        # Show dashboard by default
        self._switch_page(0, self._btn_dashboard)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(f"background-color: {_SIDEBAR_BG};")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title label
        title_label = QLabel(config.APP_TITLE)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            f"color: white; font-size: 16px; font-weight: bold; padding: 20px 10px;"
        )
        layout.addWidget(title_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #3A5A8A;")
        layout.addWidget(divider)

        # Navigation buttons
        self._btn_dashboard = QPushButton("  Dashboard")
        self._btn_clients = QPushButton("  Client Management")
        self._btn_reports = QPushButton("  Reports")

        for idx, btn in enumerate([self._btn_dashboard, self._btn_clients, self._btn_reports]):
            btn.setStyleSheet(_SIDEBAR_STYLE)
            btn.setCheckable(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            page_idx = idx  # capture
            btn.clicked.connect(lambda checked, i=page_idx, b=btn: self._switch_page(i, b))
            layout.addWidget(btn)

        layout.addStretch()

        version_label = QLabel(f"v{config.APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #7A9CC8; font-size: 11px; padding: 8px;")
        layout.addWidget(version_label)

        return sidebar

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("Welcome to GST Reconciliation")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_ACCENT};")
        layout.addWidget(title)

        subtitle = QLabel(
            "Manage your clients' GST credentials and generate reconciliation reports with ease."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #555; font-size: 14px;")
        layout.addWidget(subtitle)

        # Summary stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        self._stat_clients_label = self._build_stat_card("Total Clients", "0", stats_row)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Quick-action buttons
        quick_label = QLabel("Quick Actions")
        quick_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(quick_label)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(12)
        btn_add = QPushButton("+ Add Client")
        btn_add.setStyleSheet(_REPORT_BTN_STYLE)
        btn_add.clicked.connect(lambda: self._switch_page(1, self._btn_clients))
        quick_row.addWidget(btn_add)

        btn_reco = QPushButton("Run Reconciliation")
        btn_reco.setStyleSheet(_REPORT_BTN_STYLE)
        btn_reco.clicked.connect(lambda: self._switch_page(2, self._btn_reports))
        quick_row.addWidget(btn_reco)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        layout.addStretch()
        return page

    def _build_stat_card(self, label: str, value: str, parent_layout: QHBoxLayout) -> QLabel:
        """Create a stat card widget and return the value QLabel (for updates)."""
        card = QFrame()
        card.setStyleSheet(
            "background: white; border-radius: 10px; border: 1px solid #D0DDEE;"
        )
        card.setFixedSize(160, 90)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        val_label = QLabel(value)
        val_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        val_label.setStyleSheet(f"color: {_ACCENT};")
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #777; font-size: 12px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(val_label)
        card_layout.addWidget(lbl)
        parent_layout.addWidget(card)
        return val_label

    # ------------------------------------------------------------------
    # Client Management page
    # ------------------------------------------------------------------

    def _build_clients_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel("Client Management")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_ACCENT};")
        header_row.addWidget(title)
        header_row.addStretch()

        btn_add = QPushButton("+ Add Client")
        btn_add.setStyleSheet(_REPORT_BTN_STYLE)
        btn_add.clicked.connect(self._add_client)
        header_row.addWidget(btn_add)

        btn_edit = QPushButton("Edit")
        btn_edit.setStyleSheet(_REPORT_BTN_STYLE)
        btn_edit.clicked.connect(self._edit_client)
        header_row.addWidget(btn_edit)

        btn_del = QPushButton("Delete")
        btn_del.setStyleSheet(
            "QPushButton { background-color: #C0392B; color: white; border-radius: 6px;"
            " padding: 10px 16px; font-size: 13px; }"
            " QPushButton:hover { background-color: #A93226; }"
        )
        btn_del.clicked.connect(self._delete_client)
        header_row.addWidget(btn_del)

        layout.addLayout(header_row)

        # Client table
        self._client_table = QTableWidget()
        self._client_table.setColumnCount(4)
        self._client_table.setHorizontalHeaderLabels(["ID", "Business Name", "GSTIN", "Portal Username"])
        self._client_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._client_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._client_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._client_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._client_table.setAlternatingRowColors(True)
        self._client_table.verticalHeader().setVisible(False)
        layout.addWidget(self._client_table)

        return page

    def _refresh_client_table(self) -> None:
        """Reload client data from the database and repopulate the table."""
        clients = client_master.get_all_clients()
        self._client_table.setRowCount(len(clients))
        for row_idx, c in enumerate(clients):
            self._client_table.setItem(row_idx, 0, QTableWidgetItem(str(c.get("ClientID", ""))))
            self._client_table.setItem(row_idx, 1, QTableWidgetItem(c.get("BusinessName", "")))
            self._client_table.setItem(row_idx, 2, QTableWidgetItem(c.get("GSTIN", "")))
            self._client_table.setItem(row_idx, 3, QTableWidgetItem(c.get("PortalUsername", "")))

        # Update stat card
        self._stat_clients_label.setText(str(len(clients)))

    def _selected_client_id(self) -> Optional[int]:
        """Return the ClientID of the currently selected table row, or None."""
        selected = self._client_table.selectedItems()
        if not selected:
            return None
        row = self._client_table.currentRow()
        item = self._client_table.item(row, 0)
        if item:
            return int(item.text())
        return None

    # ------------------------------------------------------------------
    # Client CRUD actions
    # ------------------------------------------------------------------

    def _add_client(self) -> None:
        dlg = AddClientDialog(self)
        if dlg.exec() == AddClientDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                client_master.add_client(**data)
                self._refresh_client_table()
                self._status(f"Client '{data['business_name']}' added successfully.")
            except ValueError as exc:
                QMessageBox.warning(self, "Duplicate GSTIN", str(exc))
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to add client:\n{exc}")

    def _edit_client(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            QMessageBox.information(self, "No Selection", "Please select a client to edit.")
            return
        client_data = client_master.get_client_by_id(client_id)
        if client_data is None:
            QMessageBox.warning(self, "Not Found", "Client not found in database.")
            return
        dlg = EditClientDialog(client_data, self)
        if dlg.exec() == EditClientDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                client_master.edit_client(
                    client_id=data["client_id"],
                    business_name=data["business_name"],
                    gstin=data["gstin"],
                    portal_username=data["portal_username"],
                    password=data["password"],
                )
                self._refresh_client_table()
                self._status(f"Client '{data['business_name']}' updated.")
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to update client:\n{exc}")

    def _delete_client(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            QMessageBox.information(self, "No Selection", "Please select a client to delete.")
            return
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this client?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            client_master.delete_client(client_id)
            self._refresh_client_table()
            self._status("Client deleted.")

    # ------------------------------------------------------------------
    # Reports page
    # ------------------------------------------------------------------

    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(30, 30, 30, 30)
        outer_layout.setSpacing(16)

        title = QLabel("Reports")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_ACCENT};")
        outer_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 10, 10)

        def _add_report_btn(label: str, handler) -> None:
            btn = QPushButton(label)
            btn.setStyleSheet(_REPORT_BTN_STYLE)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(48)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

        _add_report_btn("GSTR-1 vs GSTR-3B Reconciliation", self._run_gstr1_vs_gstr3b)
        _add_report_btn("GSTR-1 Detailed Report (Rate-wise & Party-wise)", self._run_gstr1_detailed)
        _add_report_btn("GSTR-3B Detailed Report", self._run_gstr3b_detailed)
        _add_report_btn("GSTR-2B vs GSTR-3B vs GSTR-2A Reconciliation", self._run_3way_reco)
        _add_report_btn("Financial Year Summary", self._run_fy_summary)
        _add_report_btn("Monthly Summary", self._run_monthly_summary)

        layout.addStretch()
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll)

        return page

    # ------------------------------------------------------------------
    # Report runners
    # ------------------------------------------------------------------

    def _load_excel(self, path: str) -> pd.DataFrame:
        """Load an Excel file into a DataFrame, raising on error."""
        return pd.read_excel(path)

    def _run_gstr1_vs_gstr3b(self) -> None:
        from reconciliation.reports import gstr1_vs_gstr3b_report

        dlg = ReportOptionsDialog(
            title="GSTR-1 vs GSTR-3B",
            file_labels=["GSTR-1 Excel File", "GSTR-3B Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        try:
            self._status("Running GSTR-1 vs GSTR-3B reconciliation…")
            QApplication.processEvents()
            df1 = self._load_excel(paths[0])
            df3b = self._load_excel(paths[1])
            out = gstr1_vs_gstr3b_report(df1, df3b)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    def _run_gstr1_detailed(self) -> None:
        from reconciliation.reports import gstr1_detailed_report

        dlg = ReportOptionsDialog(
            title="GSTR-1 Detailed Report",
            file_labels=["GSTR-1 Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        try:
            self._status("Generating GSTR-1 Detailed Report…")
            QApplication.processEvents()
            df = self._load_excel(paths[0])
            out = gstr1_detailed_report(df)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    def _run_gstr3b_detailed(self) -> None:
        from reconciliation.reports import gstr3b_detailed_report

        dlg = ReportOptionsDialog(
            title="GSTR-3B Detailed Report",
            file_labels=["GSTR-3B Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        try:
            self._status("Generating GSTR-3B Detailed Report…")
            QApplication.processEvents()
            df = self._load_excel(paths[0])
            out = gstr3b_detailed_report(df)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    def _run_3way_reco(self) -> None:
        from reconciliation.reports import gstr2b_vs_gstr3b_vs_gstr2a_report

        dlg = ReportOptionsDialog(
            title="GSTR-2B vs GSTR-3B vs GSTR-2A",
            file_labels=["GSTR-2B Excel File", "GSTR-3B Excel File", "GSTR-2A Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        try:
            self._status("Running 3-way reconciliation…")
            QApplication.processEvents()
            df2b = self._load_excel(paths[0])
            df3b = self._load_excel(paths[1])
            df2a = self._load_excel(paths[2])
            out = gstr2b_vs_gstr3b_vs_gstr2a_report(df2b, df3b, df2a)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    def _run_fy_summary(self) -> None:
        from reconciliation.reports import financial_year_summary

        dlg = ReportOptionsDialog(
            title="Financial Year Summary",
            file_labels=["Data Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        fy = dlg.get_financial_year()
        try:
            self._status(f"Generating FY {fy} Summary…")
            QApplication.processEvents()
            df = self._load_excel(paths[0])
            out = financial_year_summary(df, financial_year=fy)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    def _run_monthly_summary(self) -> None:
        from reconciliation.reports import monthly_summary

        dlg = ReportOptionsDialog(
            title="Monthly Summary",
            file_labels=["Data Excel File"],
            parent=self,
        )
        if dlg.exec() != ReportOptionsDialog.DialogCode.Accepted:
            return
        paths = dlg.get_file_paths()
        try:
            self._status("Generating Monthly Summary…")
            QApplication.processEvents()
            df = self._load_excel(paths[0])
            out = monthly_summary(df)
            self._status(f"Report saved: {out}")
            QMessageBox.information(self, "Done", f"Report saved:\n{out}")
        except Exception as exc:
            self._show_error(exc)

    # ------------------------------------------------------------------
    # Sidebar navigation
    # ------------------------------------------------------------------

    def _switch_page(self, index: int, active_btn: QPushButton) -> None:
        self._stack.setCurrentIndex(index)
        for btn in [self._btn_dashboard, self._btn_clients, self._btn_reports]:
            btn.setProperty("active", btn is active_btn)
            btn.setStyle(btn.style())  # force style refresh

        # Refresh client table whenever Clients page is shown
        if index == 1:
            self._refresh_client_table()

        # Also update stat card when switching to dashboard
        if index == 0:
            clients = client_master.get_all_clients()
            self._stat_clients_label.setText(str(len(clients)))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _status(self, message: str) -> None:
        self._status_bar.showMessage(message)

    def _show_error(self, exc: Exception) -> None:
        tb = traceback.format_exc()
        self._status(f"Error: {exc}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{exc}\n\n{tb}")
