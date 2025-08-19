# 🎬 sonarr-lang-checker

[Italiano](README.it.md) · English

Check for **audio language discrepancies** across episodes within a season, or across seasons of a TV series, using the [Sonarr v4](https://sonarr.tv) API.

---

## 🚀 Features

- 🔍 Scans all series and seasons in Sonarr (v4)
- 🎧 Detects episodes or seasons with mixed audio languages (e.g., half Italian, half English)
- 📦 Outputs either human‑readable text or JSON
- 🧰 Works smoothly with `uv` for fast, isolated Python environments

> ❗ Compatible only with **Sonarr v4** (`/api/v3`). Sonarr v3 or lower is not supported.

---

## ⚙️ Requirements

- [uv](https://github.com/astral-sh/uv) installed (e.g., `brew install uv` or the official install script)
- Python 3.8+

---

## 📦 Setup

### Clone the project

```bash
git clone https://github.com/alsd4git/sonarr-lang-checker.git
cd sonarr-lang-checker
```

## ▶️ Usage

```bash
uv run ./main.py --apikey <API_KEY> --url <https://host> [options]
```

### 🔑 Available options

| Flag             | Description                                                                  |
|------------------|------------------------------------------------------------------------------|
| `--apikey`       | **(required)** Sonarr API key (Settings → General)                          |
| `--url`          | **(required)** Sonarr v4 base URL (e.g., https://sonarr.example.org)        |
| `--output`       | Save output to a `.json` file                                               |
| `--json`         | Print output as JSON to stdout                                              |
| `--show-all`     | Show monolingual seasons as well, not only mixed‑language ones              |
| `-h, --help`     | Show help and all available parameters                                      |

---

### 💡 Examples

Basic scan:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org
```

JSON output:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org --json
```

Save output to file:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org --output risultati.json
```

---

## 🧪 Optional wrapper: `run.sh`

For convenience:

```bash
./run.sh --apikey abc123 --url https://sonarr.example.org --output out.json
```

---

## 🌍 .env configuration

You can define the API key and URL in a `.env` file:

```
API_KEY=abc123
SONARR_URL=https://sonarr.example.org
```

The script will automatically load these values if not provided via CLI.

## 🧱 Project structure

```bash
sonarr-lang-checker/
├── main.py            # Main script (Sonarr v4 only)
├── pyproject.toml     # Dependencies for uv
├── run.sh             # Convenience wrapper
├── .env.example       # Example env vars
├── language_flags.py  # Map language codes → emoji
└── README.md
```

---

## 📌 Future ideas

- `cron` support for scheduled runs
- `Dockerfile` for containerization
- Web UI or interactive CLI with advanced filtering
- Telegram/email notifications for detected mismatches
- Language code normalization and flags
- CSV export
- `.env` support already included ✅

---

## 🤝 Contribute

Pull requests and suggestions are welcome!

---

## 🛡️ License

MIT License - Do what you want, just credit the author :)
© [Alessandro Digilio](https://github.com/alsd4git)
