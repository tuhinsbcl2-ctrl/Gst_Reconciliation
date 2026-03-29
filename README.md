# GST Reconciliation Desktop Application

A full-featured **desktop application** for chartered accountants and tax professionals to manage GST client credentials and generate reconciliation reports — all from Excel files, with no portal login required.

---

## Features

- **Client Vault** — Securely store client GSTIN, portal username, and encrypted password (AES-256 via Fernet).
- **GSTR-1 vs GSTR-3B Reconciliation** — Compare sales declared in GSTR-1 with tax paid in GSTR-3B; period-wise mismatch detection.
- **GSTR-1 Detailed Report** — Rate-wise (5%, 12%, 18%, 28%) and Party-wise summary with monthly and FY breakdowns.
- **GSTR-3B Detailed Report** — Monthly outward supply, tax liability, and ITC summary.
- **GSTR-2B vs GSTR-3B vs GSTR-2A Reconciliation** — Three-way ITC comparison: available vs claimed vs auto-populated.
- **Financial Year Summary** — Aggregated view across April–March for any selected FY.
- **Monthly Summary** — Month-by-month breakdown of any return data.
- **Excel Export** — All reports exported to colour-coded, formatted `.xlsx` files using `openpyxl`.

---

## Installation

### Prerequisites

- Python 3.10 or later
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/tuhinsbcl2-ctrl/Gst_Reconciliation.git
cd Gst_Reconciliation

# 2. (Recommended) Create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```bash
python main.py
```

The SQLite database (`data/gst_reconciliation.db`) and the encryption key (`data/.secret.key`) are created automatically on first launch.

---

## Screenshots

> *Screenshots will be added after UI stabilisation.*

---

## Project Structure

```
Gst_Reconciliation/
├── main.py                         # Application entry point
├── config.py                       # DB path, encryption key, GSP API placeholders
├── requirements.txt
├── GSTR App.txt                    # Gemini conversation reference
│
├── database/
│   ├── __init__.py
│   └── client_master.py            # SQLite CRUD + Fernet encryption
│
├── reconciliation/
│   ├── __init__.py
│   ├── engine.py                   # Pandas reconciliation logic
│   └── reports.py                  # Excel report generation (openpyxl)
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # PyQt6 main window with sidebar
│   └── dialogs.py                  # Add/Edit Client & Report Options dialogs
│
└── data/                           # Created automatically at runtime
    ├── gst_reconciliation.db
    └── .secret.key
```

---

## Compliance Note

> Direct credential-based login to the GST Portal from a third-party application is **not** supported via public APIs.  
> To automate data pulling, you must integrate with a **GST Suvidha Provider (GSP)** such as [ClearTax](https://cleartax.in), [Cygnet](https://cygnetgsp.in), or [Masters India](https://mastersindia.co).  
> The current version supports **Excel-based** reconciliation immediately. GSP integration is planned as a future enhancement.

---

## Future Roadmap

- [ ] GSP API integration for direct data pulling (GSTR-1, 2A, 2B, 3B)
- [ ] OTP session management for GST portal authentication
- [ ] Automated monthly data download and scheduling
- [ ] PDF export support
- [ ] Email delivery of reports
- [ ] Multi-user support with role-based access

---

## License

This project is for internal/personal use. No licence is currently specified.
