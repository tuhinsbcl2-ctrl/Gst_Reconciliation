"""
database/client_master.py — SQLite-based Client Vault for GST Reconciliation App.

Provides CRUD operations for the `clients` table and encrypts/decrypts
passwords using the Fernet symmetric-encryption scheme (cryptography library).
"""

import sqlite3
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet

import config


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """Return a Fernet instance initialised with the application key."""
    key = config.get_or_create_fernet_key()
    return Fernet(key)


def _encrypt(plaintext: str) -> str:
    """Encrypt *plaintext* and return a UTF-8 token string."""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def _decrypt(token: str) -> str:
    """Decrypt a Fernet *token* and return the original plaintext."""
    fernet = _get_fernet()
    return fernet.decrypt(token.encode()).decode()


def _get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row_factory set to Row."""
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the `clients` table if it does not already exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS clients (
        ClientID         INTEGER PRIMARY KEY AUTOINCREMENT,
        BusinessName     TEXT    NOT NULL,
        GSTIN            TEXT    NOT NULL UNIQUE,
        PortalUsername   TEXT    NOT NULL,
        EncryptedPassword TEXT   NOT NULL,
        AuthToken        TEXT,
        CreatedAt        TEXT    NOT NULL,
        UpdatedAt        TEXT    NOT NULL
    );
    """
    with _get_connection() as conn:
        conn.execute(ddl)
        conn.commit()


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def add_client(
    business_name: str,
    gstin: str,
    portal_username: str,
    password: str,
    auth_token: str = "",
) -> int:
    """Insert a new client record.

    Args:
        business_name: Legal name of the business.
        gstin: 15-character GST Identification Number.
        portal_username: Login username for GST portal.
        password: Plain-text password (will be encrypted before storage).
        auth_token: Optional auth/session token (stored as-is).

    Returns:
        The auto-assigned ClientID.

    Raises:
        ValueError: If *gstin* is already registered.
    """
    now = datetime.utcnow().isoformat()
    encrypted_pw = _encrypt(password)

    sql = """
    INSERT INTO clients
        (BusinessName, GSTIN, PortalUsername, EncryptedPassword, AuthToken, CreatedAt, UpdatedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                sql,
                (business_name, gstin.upper(), portal_username, encrypted_pw, auth_token, now, now),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"A client with GSTIN '{gstin}' already exists.") from exc


def edit_client(
    client_id: int,
    business_name: Optional[str] = None,
    gstin: Optional[str] = None,
    portal_username: Optional[str] = None,
    password: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> bool:
    """Update fields of an existing client.

    Only non-None arguments are updated.  Returns True if a row was modified,
    False if *client_id* does not exist.
    """
    fields: list[str] = []
    values: list = []

    if business_name is not None:
        fields.append("BusinessName = ?")
        values.append(business_name)
    if gstin is not None:
        fields.append("GSTIN = ?")
        values.append(gstin.upper())
    if portal_username is not None:
        fields.append("PortalUsername = ?")
        values.append(portal_username)
    if password is not None:
        fields.append("EncryptedPassword = ?")
        values.append(_encrypt(password))
    if auth_token is not None:
        fields.append("AuthToken = ?")
        values.append(auth_token)

    if not fields:
        return False  # nothing to update

    fields.append("UpdatedAt = ?")
    values.append(datetime.utcnow().isoformat())
    values.append(client_id)

    sql = f"UPDATE clients SET {', '.join(fields)} WHERE ClientID = ?"
    with _get_connection() as conn:
        cursor = conn.execute(sql, values)
        conn.commit()
        return cursor.rowcount > 0


def delete_client(client_id: int) -> bool:
    """Delete a client by *client_id*.

    Returns True if a row was deleted, False otherwise.
    """
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM clients WHERE ClientID = ?", (client_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_all_clients() -> list[dict]:
    """Return a list of all clients as plain dicts (password decrypted)."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM clients ORDER BY BusinessName"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_client_by_id(client_id: int) -> Optional[dict]:
    """Return a single client dict for *client_id*, or None if not found."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE ClientID = ?", (client_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_client_by_gstin(gstin: str) -> Optional[dict]:
    """Return a single client dict matching *gstin* (case-insensitive), or None."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE GSTIN = ?", (gstin.upper(),)
        ).fetchone()
    return _row_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# Internal conversion helper
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict, decrypting the password field."""
    d = dict(row)
    try:
        d["Password"] = _decrypt(d.pop("EncryptedPassword", ""))
    except Exception:
        d["Password"] = ""
    return d
