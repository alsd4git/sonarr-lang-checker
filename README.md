# 🎬 sonarr-lang-checker

Controlla se ci sono **discrepanze linguistiche** tra gli episodi nelle stagioni o tra stagioni di una serie TV, usando l'API di [Sonarr v4](https://sonarr.tv).

---

## 🚀 Caratteristiche

- 🔍 Analizza tutte le serie e stagioni presenti in Sonarr (v4)
- 🎧 Rileva episodi o stagioni con lingue miste (es. metà in italiano, metà in inglese)
- 📦 Output in formato testuale o JSON
- 🧰 Compatibile con `uv` per gestione ambienti veloce e isolata

> ❗ Compatibile solo con **Sonarr v4** (`/api/v3`). Non supporta Sonarr v3 o inferiore.

---

## ⚙️ Requisiti

- [uv](https://github.com/astral-sh/uv) installato (via `cargo install uv` o `brew install uv`)
- Python 3.8+

---

## 📦 Setup

### Clona il progetto

```bash
git clone https://github.com/alsd4git/sonarr-lang-checker.git
cd sonarr-lang-checker
```

## ▶️ Utilizzo

```bash
uv run ./main.py --apikey <API_KEY> --url <https://host> [opzioni]
```

### 🔑 Opzioni disponibili

| Flag             | Descrizione                                                                 |
|------------------|------------------------------------------------------------------------------|
| `--apikey`       | **(obbligatorio)** API key di Sonarr (Settings → General)                   |
| `--url`          | **(obbligatorio)** URL base Sonarr v4 (es: https://sonarr.example.org)      |
| `--output`       | Salva l’output su un file `.json`                                           |
| `--json`         | Mostra l’output direttamente in formato JSON su stdout                      |
| `--show-all`     | Mostra anche stagioni monolingua, non solo quelle con lingue miste          |
| `-h, --help`     | Mostra l’aiuto e tutti i parametri disponibili                              |

---

### 💡 Esempi

Analisi base:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org
```

Output formattato in JSON:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org --json
```

Output salvato su file:

```bash
uv run ./main.py --apikey abc123 --url https://sonarr.example.org --output risultati.json
```

---

## 🧪 Wrapper opzionale: `run.sh`

Per semplificare l’uso:

```bash
./run.sh --apikey abc123 --url https://sonarr.example.org --output out.json
```

---

## 🌍 Configurazione .env

Puoi definire API key e URL direttamente in un file `.env`:

```
API_KEY=abc123
SONARR_URL=https://sonarr.example.org
```

Lo script caricherà questi valori automaticamente se non specificati da CLI.

## 🧱 Struttura del progetto

```bash
sonarr-lang-checker/
├── main.py            # Script principale (solo Sonarr v4)
├── pyproject.toml     # Definizione dipendenze per uv
├── run.sh             # Wrapper eseguibile
├── .env.example       # File di esempio per le variabili d’ambiente
├── language_flags.py  # Mappatura codici lingua → emoji
└── README.md
```

---

## 📌 Estensioni future (idee)

- Supporto `cron` per esecuzione pianificata
- `Dockerfile` per containerizzazione
- Web UI o CLI interattiva con ricerca avanzata
- Notifiche Telegram/email per mismatch rilevati
- Normalizzazione codici lingua e bandierine
- Esportazione CSV
- Supporto `.env` già integrato ✅

---

## 🤝 Contribuire

Pull request e suggerimenti sono benvenuti!

---

## 🛡️ Licenza

MIT License - Fai quello che vuoi, ma linka l'autore :)
© [Alessandro Digilio](https://github.com/alsd4git)
