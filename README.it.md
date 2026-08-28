# sonarr-lang-checker

[English](README.en.md) · Italiano

[![CI](https://github.com/alsd4git/sonarr-lang-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/alsd4git/sonarr-lang-checker/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Individua coperture audio incoerenti in una libreria Sonarr v4. Lo script segnala stagioni con lingue miste, confronta le stagioni di una serie e verifica se gli episodi contengono un insieme di lingue desiderate.

È richiesto Sonarr v4. Le versioni precedenti non sono supportate.

## Requisiti

- Python 3.10 o successivo
- [uv](https://docs.astral.sh/uv/)
- URL e API key di Sonarr v4

## Configurazione

```bash
git clone https://github.com/alsd4git/sonarr-lang-checker.git
cd sonarr-lang-checker
cp .env.example .env
uv sync --locked
```

Imposta questi valori in `.env`:

```dotenv
API_KEY=inserisci-la-tua-api-key
SONARR_URL=https://sonarr.example.org
```

Mantieni privato il file `.env`. Una API key passata come argomento può essere salvata nella cronologia della shell o comparire nella lista dei processi.

## Utilizzo

```bash
# Analisi standard
uv run python main.py

# Stampa JSON su stdout
uv run python main.py --json

# Salva risultati strutturati, inclusi i metadati degli errori parziali
uv run python main.py --structured-json --output report.json

# Segnala la copertura italiana e inglese mancante o parziale
uv run python main.py --wanted-langs ita,eng

# Include le stagioni che soddisfano tutte le lingue richieste
uv run python main.py --wanted-langs ita,eng --show-all

# Riduce le richieste concorrenti verso Sonarr
uv run python main.py --workers 2
```

Usa `uv run python main.py --help` per l'elenco completo delle opzioni. Sui sistemi POSIX, `./run.sh` è un wrapper più breve.

### Opzioni principali

| Opzione | Scopo |
| --- | --- |
| `--json` | Stampa su stdout il formato JSON originale. |
| `--structured-json` | Include i metadati `results`, `failures` e `complete`. |
| `--output PERCORSO` | Scrive l'output JSON in un file. |
| `--wanted-langs ELENCO` | Verifica un elenco separato da virgole, per esempio `ita,eng`. |
| `--show-all` | Include le stagioni monolingua o con copertura completa. |
| `--ignore-unknown` | Esclude le tracce sconosciute dal confronto delle lingue. |
| `--ignore-anime` | Ignora le serie con tipo Anime in Sonarr. |
| `--workers N` | Limita le richieste concorrenti. Il valore predefinito è 4, il massimo è 16. |
| `--timeout SECONDI` | Imposta il timeout di lettura HTTP. |

I codici lingua vengono normalizzati prima del confronto. L'ordine delle tracce non conta, gli alias comuni vengono unificati e le tracce sconosciute usano `und`.

## Codici di uscita

| Codice | Significato |
| --- | --- |
| `0` | L'analisi è stata completata. |
| `1` | Un errore fatale di configurazione o richiesta ha impedito l'analisi. |
| `2` | Sono stati prodotti risultati parziali perché non è stato possibile recuperare una o più serie. |

Gli errori e il riepilogo dei risultati parziali vengono scritti su stderr, così il JSON su stdout resta leggibile dalle applicazioni.

## Sviluppo

```bash
uv sync --locked --dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

GitHub Actions esegue questi controlli su Linux, macOS e Windows con la versione Python minima e quella più recente supportate.

## Licenza

Distribuito con licenza [MIT](LICENSE).
