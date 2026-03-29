"""
ui/dialogs.py — PyQt6 dialogs for GST Reconciliation App.

Provides:
    AddClientDialog    — Form for adding a new client.
    EditClientDialog   — Form for editing an existing client.
    ReportOptionsDialog — Select FY, month range, and input files before generating a report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


# ---------------------------------------------------------------------------
# AddClientDialog
# ---------------------------------------------------------------------------

class AddClientDialog(QDialog):
    """Modal dialog for adding a new GST client."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Client")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. ABC Enterprises Pvt Ltd")
        form.addRow("Business Name *", self._name_edit)

        self._gstin_edit = QLineEdit()
        self._gstin_edit.setPlaceholderText("15-character GSTIN")
        self._gstin_edit.setMaxLength(15)
        form.addRow("GSTIN *", self._gstin_edit)

        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("GST Portal username")
        form.addRow("Portal Username *", self._user_edit)

        self._pass_edit = QLineEdit()
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_edit.setPlaceholderText("GST Portal password")
        form.addRow("Password *", self._pass_edit)

        layout.addLayout(form)

        # Standard OK / Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Public getters
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        """Return entered data as a dict."""
        return {
            "business_name": self._name_edit.text().strip(),
            "gstin": self._gstin_edit.text().strip().upper(),
            "portal_username": self._user_edit.text().strip(),
            "password": self._pass_edit.text(),
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_and_accept(self) -> None:
        data = self.get_data()
        if not data["business_name"]:
            QMessageBox.warning(self, "Validation Error", "Business Name is required.")
            return
        if len(data["gstin"]) != 15:
            QMessageBox.warning(self, "Validation Error", "GSTIN must be exactly 15 characters.")
            return
        if not data["portal_username"]:
            QMessageBox.warning(self, "Validation Error", "Portal Username is required.")
            return
        if not data["password"]:
            QMessageBox.warning(self, "Validation Error", "Password is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# EditClientDialog
# ---------------------------------------------------------------------------

class EditClientDialog(QDialog):
    """Modal dialog for editing an existing GST client.

    Pre-populates the form with *client_data*.
    """

    def __init__(self, client_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Client")
        self.setMinimumWidth(420)
        self._client_id: int = client_data.get("ClientID", -1)
        self._build_ui(client_data)

    def _build_ui(self, data: dict) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_edit = QLineEdit(data.get("BusinessName", ""))
        form.addRow("Business Name *", self._name_edit)

        self._gstin_edit = QLineEdit(data.get("GSTIN", ""))
        self._gstin_edit.setMaxLength(15)
        form.addRow("GSTIN *", self._gstin_edit)

        self._user_edit = QLineEdit(data.get("PortalUsername", ""))
        form.addRow("Portal Username *", self._user_edit)

        self._pass_edit = QLineEdit(data.get("Password", ""))
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_edit.setPlaceholderText("Leave blank to keep current password")
        form.addRow("Password", self._pass_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Public getters
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        """Return edited data as a dict.  Password is None if field left blank."""
        pw = self._pass_edit.text()
        return {
            "client_id": self._client_id,
            "business_name": self._name_edit.text().strip(),
            "gstin": self._gstin_edit.text().strip().upper(),
            "portal_username": self._user_edit.text().strip(),
            "password": pw if pw else None,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_and_accept(self) -> None:
        data = self.get_data()
        if not data["business_name"]:
            QMessageBox.warning(self, "Validation Error", "Business Name is required.")
            return
        if len(data["gstin"]) != 15:
            QMessageBox.warning(self, "Validation Error", "GSTIN must be exactly 15 characters.")
            return
        if not data["portal_username"]:
            QMessageBox.warning(self, "Validation Error", "Portal Username is required.")
            return
        self.accept()


# ---------------------------------------------------------------------------
# ReportOptionsDialog
# ---------------------------------------------------------------------------

_MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March",
]

_CURRENT_FY_START = 2023  # Will be overridden dynamically


def _build_fy_options() -> list[str]:
    """Return a list of financial year strings for the last 5 years."""
    import datetime
    year = datetime.date.today().year
    month = datetime.date.today().month
    # If after April, current FY starts this year; otherwise starts previous year
    start = year if month >= 4 else year - 1
    return [f"{y}-{str(y + 1)[2:]}" for y in range(start, start - 6, -1)]


class ReportOptionsDialog(QDialog):
    """Dialog to select report parameters: financial year, month range, and input files."""

    def __init__(
        self,
        title: str = "Report Options",
        file_labels: Optional[list[str]] = None,
        parent=None,
    ) -> None:
        """
        Args:
            title:       Window title.
            file_labels: Labels for each file-picker row, e.g. ["GSTR-1 File", "GSTR-3B File"].
                         If None, a single generic file picker is shown.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self._file_edits: list[QLineEdit] = []
        self._build_ui(file_labels or ["Input Excel File"])

    def _build_ui(self, file_labels: list[str]) -> None:
        layout = QVBoxLayout(self)

        # ---- Financial Year ----
        fy_group = QGroupBox("Financial Year")
        fy_layout = QFormLayout(fy_group)
        self._fy_combo = QComboBox()
        self._fy_combo.addItems(_build_fy_options())
        fy_layout.addRow("Financial Year:", self._fy_combo)
        layout.addWidget(fy_group)

        # ---- Month Range ----
        month_group = QGroupBox("Month Range (optional)")
        month_layout = QHBoxLayout(month_group)
        self._from_month = QComboBox()
        self._from_month.addItems(["All"] + _MONTHS)
        self._to_month = QComboBox()
        self._to_month.addItems(["All"] + _MONTHS)
        month_layout.addWidget(QLabel("From:"))
        month_layout.addWidget(self._from_month)
        month_layout.addWidget(QLabel("To:"))
        month_layout.addWidget(self._to_month)
        layout.addWidget(month_group)

        # ---- Input Files ----
        files_group = QGroupBox("Input Files")
        files_layout = QFormLayout(files_group)
        for label in file_labels:
            row_widget = QWidget_()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            edit.setPlaceholderText("Click Browse to select Excel file…")
            btn = QPushButton("Browse")
            # Capture the edit reference via default arg
            btn.clicked.connect(lambda checked, e=edit: self._browse_file(e))
            row_layout.addWidget(edit)
            row_layout.addWidget(btn)
            files_layout.addRow(label + ":", row_widget)
            self._file_edits.append(edit)
        layout.addWidget(files_group)

        # ---- Buttons ----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _browse_file(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if path:
            edit.setText(path)

    def _validate_and_accept(self) -> None:
        for edit in self._file_edits:
            if not edit.text().strip():
                QMessageBox.warning(self, "Validation Error", "Please select all required input files.")
                return
        self.accept()

    # ------------------------------------------------------------------
    # Public getters
    # ------------------------------------------------------------------

    def get_financial_year(self) -> str:
        return self._fy_combo.currentText()

    def get_month_range(self) -> tuple[str, str]:
        return self._from_month.currentText(), self._to_month.currentText()

    def get_file_paths(self) -> list[str]:
        return [e.text().strip() for e in self._file_edits]


# ---------------------------------------------------------------------------
# Tiny helper widget to allow row_widget inline creation in the form layout
# ---------------------------------------------------------------------------

from PyQt6.QtWidgets import QWidget as QWidget_
