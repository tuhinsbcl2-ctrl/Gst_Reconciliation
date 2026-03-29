"""
config.py — Application-wide configuration for GST Reconciliation App.

Manages database path, encryption key, default settings, and GSP API placeholders.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Base directory of this file
BASE_DIR = Path(__file__).resolve().parent

# SQLite database file
DB_PATH = BASE_DIR / "data" / "gst_reconciliation.db"

# Directory for generated Excel reports
REPORTS_DIR = BASE_DIR / "reports"

# File that stores the persistent Fernet encryption key
KEY_FILE = BASE_DIR / "data" / ".secret.key"

# Ensure required directories exist at import time
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def get_or_create_fernet_key() -> bytes:
    """Return the Fernet key, generating and persisting it if it doesn't exist yet.

    The key is stored in KEY_FILE.  On first run the file is created with
    restricted permissions so that only the current user can read it.
    """
    from cryptography.fernet import Fernet

    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    # Restrict permissions to owner-read/write only (Unix)
    try:
        os.chmod(KEY_FILE, 0o600)
    except AttributeError:
        pass  # Windows — skip chmod
    return key

# ---------------------------------------------------------------------------
# Default financial year settings
# ---------------------------------------------------------------------------

# Financial year starts in April
FY_START_MONTH = 4  # April

# Default number of recent months to display in summary views
DEFAULT_MONTHS_DISPLAY = 12

# Available GST tax rates used for rate-wise grouping
GST_TAX_RATES = [0, 5, 12, 18, 28]

# ---------------------------------------------------------------------------
# GSP (GST Suvidha Provider) API — placeholder for future integration
# ---------------------------------------------------------------------------

GSP_API_BASE_URL = os.environ.get("GSP_API_BASE_URL", "https://api.example-gsp.com/v1")
GSP_API_KEY = os.environ.get("GSP_API_KEY", "")  # Set via environment variable
GSP_APP_KEY = os.environ.get("GSP_APP_KEY", "")  # Application key issued by GSP

# ---------------------------------------------------------------------------
# UI settings
# ---------------------------------------------------------------------------

APP_TITLE = "GST Reconciliation"
APP_VERSION = "1.0.0"
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 680
