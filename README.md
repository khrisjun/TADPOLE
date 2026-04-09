# TADPOLE – TAID And Data Product Lookup Engine

A Microsoft Teams bot that converts a **TAID** (Technology Asset Identifier) into
the corresponding **RS Code** (Resource/Service Code).  
Data can be served from **Snowflake**, **Oracle (TLS 1.2)**, or a **CSV / SQLite fallback**.

---

## Features

| Feature | Details |
|---|---|
| Teams bot | Built with the Microsoft Bot Framework SDK 4.x |
| Multi-source lookup | Snowflake → Oracle → CSV (auto-priority or pinned via env var) |
| Oracle TLS 1.2 | Enforced via Oracle Wallet / PEM certificate bundle |
| CSV fallback | No external DB required; ships with sample data |
| Lightweight | Pure Python, no Oracle Client install needed (`oracledb` thin mode) |

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.9+ |
| pip | any |
| ngrok (local dev) | [ngrok.com](https://ngrok.com) |
| Bot Framework Emulator | [Download](https://github.com/microsoft/BotFramework-Emulator/releases) |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/khrisjun/TADPOLE.git
cd TADPOLE
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Key variables:

| Variable | Description |
|---|---|
| `MicrosoftAppId` | Bot App ID (leave blank for Emulator) |
| `MicrosoftAppPassword` | Bot App Password (leave blank for Emulator) |
| `DATA_SOURCE` | `snowflake`, `oracle`, `csv`, or blank (auto) |
| `CSV_PATH` | Path to your CSV mapping file |

### 3. Run the bot

```bash
python app.py
```

The bot listens on **http://localhost:3978/api/messages**.

### 4. Connect via Bot Framework Emulator (local dev)

1. Open the Bot Framework Emulator.
2. Click **Open Bot** → enter `http://localhost:3978/api/messages`.
3. Leave App ID and Password blank (local testing).
4. Send a message such as `TAID-001`.

### 5. Expose publicly with ngrok (Teams testing)

```bash
ngrok http 3978
```

Use the generated `https://xxxx.ngrok.io` URL as your bot's messaging endpoint
in the Azure Bot resource (append `/api/messages`).

---

## Data Sources

### Snowflake

Set `DATA_SOURCE=snowflake` (or leave blank for auto-detect) and populate:

```dotenv
SNOWFLAKE_ACCOUNT=myorg-myaccount
SNOWFLAKE_USER=botuser
SNOWFLAKE_PASSWORD=s3cr3t
SNOWFLAKE_DATABASE=MY_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_TABLE=TAID_RS_MAPPING
SNOWFLAKE_TAID_COLUMN=TAID
SNOWFLAKE_RS_COLUMN=RS_CODE
```

Expected table schema:

```sql
CREATE TABLE TAID_RS_MAPPING (
    TAID    VARCHAR NOT NULL,
    RS_CODE VARCHAR NOT NULL
);
```

### Oracle (TLS 1.2)

Set `DATA_SOURCE=oracle` and populate:

```dotenv
ORACLE_DSN=db.example.com:1521/ORCL
ORACLE_USER=botuser
ORACLE_PASSWORD=s3cr3t
ORACLE_WALLET_DIR=/path/to/wallet   # directory with cwallet.sso / CA certs
ORACLE_TABLE=TAID_RS_MAPPING
ORACLE_TAID_COLUMN=TAID
ORACLE_RS_COLUMN=RS_CODE
```

`ORACLE_WALLET_DIR` is used to enforce TLS 1.2:
- Point it at an **Oracle Wallet** directory (contains `cwallet.sso`), **or**
- A directory containing a PEM CA certificate bundle recognised by `python-oracledb` thin mode.

Expected table schema:

```sql
CREATE TABLE TAID_RS_MAPPING (
    TAID    VARCHAR2(100) NOT NULL,
    RS_CODE VARCHAR2(100) NOT NULL
);
```

### CSV / SQLite Fallback

The default data source – no credentials required.

```dotenv
DATA_SOURCE=csv
CSV_PATH=data/sample_taid_rs_codes.csv
CSV_TAID_COLUMN=TAID
CSV_RS_COLUMN=RS_CODE
```

The CSV is loaded into an in-memory SQLite database on startup and cached for
the lifetime of the process. To refresh without restarting, call
`data.csv_connector.reload(config)`.

Sample CSV format:

```csv
TAID,RS_CODE
TAID-001,RS-A100
TAID-002,RS-B200
```

---

## Bot Usage (in Teams / Emulator)

| Message | Bot response |
|---|---|
| `TAID-001` | ✅ **TAID-001** → **RS-A100** |
| `convert TAID-005` | ✅ **TAID-005** → **RS-E500** |
| `what is the RS code for TAID-003?` | ✅ **TAID-003** → **RS-C300** |
| `TAID-UNKNOWN` | ⚠️ No RS Code found for **TAID-UNKNOWN** |
| `help` | Displays usage instructions |

---

## Project Structure

```
TADPOLE/
├── app.py                        # aiohttp web server & Bot Framework wiring
├── bot.py                        # TAIDBot – message handler
├── config.py                     # Environment-based configuration
├── requirements.txt
├── .env.example                  # Template environment file
├── data/
│   ├── lookup.py                 # Unified lookup interface (multi-source)
│   ├── snowflake_connector.py    # Snowflake backend
│   ├── oracle_connector.py       # Oracle backend (TLS 1.2)
│   ├── csv_connector.py          # CSV / SQLite backend
│   └── sample_taid_rs_codes.csv  # Sample mapping data
└── tests/
    └── test_bot.py               # Unit tests
```

---

## Running Tests

```bash
pip install pytest pandas
python -m pytest tests/ -v
```

---

## Deploying to Azure (Teams)

1. Create an **Azure Bot** resource → note the App ID and secret.
2. Set `MicrosoftAppId` and `MicrosoftAppPassword` in `.env`.
3. Deploy the app (Azure App Service, Container App, etc.).
4. Set the messaging endpoint in the Azure Bot to `https://<your-domain>/api/messages`.
5. Add the **Microsoft Teams** channel in the Azure Bot → **Channels** blade.
6. Install the bot in your Teams tenant via **Apps** → **Manage your apps**.
