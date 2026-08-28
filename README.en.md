# sonarr-lang-checker

English · [Italiano](README.it.md)

Find inconsistent audio-language coverage in a Sonarr v4 library. The script reports mixed-language seasons, compares seasons within a series, and checks whether episodes contain a requested set of languages.

Sonarr v4 is required. Earlier versions are not supported.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)
- A Sonarr v4 URL and API key

## Setup

```bash
git clone https://github.com/alsd4git/sonarr-lang-checker.git
cd sonarr-lang-checker
cp .env.example .env
uv sync --locked
```

Set the following values in `.env`:

```dotenv
API_KEY=replace-with-your-api-key
SONARR_URL=https://sonarr.example.org
```

Keep `.env` private. API keys passed as command-line arguments may be recorded in shell history or process listings.

## Usage

```bash
# Standard scan
uv run python main.py

# Print JSON to stdout
uv run python main.py --json

# Save structured results, including partial-failure metadata
uv run python main.py --structured-json --output report.json

# Report missing or partial Italian and English coverage
uv run python main.py --wanted-langs ita,eng

# Include seasons that fully match the requested languages
uv run python main.py --wanted-langs ita,eng --show-all

# Reduce concurrent Sonarr requests
uv run python main.py --workers 2
```

Use `uv run python main.py --help` for the complete option list. `./run.sh` is a shorter wrapper for POSIX systems.

### Relevant options

| Option | Purpose |
| --- | --- |
| `--json` | Print the legacy JSON result shape to stdout. |
| `--structured-json` | Include `results`, `failures`, and `complete` metadata. |
| `--output PATH` | Write JSON output to a file. |
| `--wanted-langs LIST` | Check a comma-separated set such as `ita,eng`. |
| `--show-all` | Include monolingual or fully covered seasons. |
| `--ignore-unknown` | Exclude unknown audio tracks from language comparisons. |
| `--ignore-anime` | Skip series whose Sonarr type is Anime. |
| `--workers N` | Limit concurrent requests. The default is 4 and the maximum is 16. |
| `--timeout SECONDS` | Set the HTTP read timeout. |

Language codes are normalized before comparison. Track order does not matter, common aliases are unified, and unknown tracks use `und`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The analysis completed. |
| `1` | A fatal configuration or request error prevented the analysis. |
| `2` | Partial results were produced because one or more series could not be fetched. |

Errors and partial-result summaries are written to stderr so JSON on stdout stays machine-readable.

## Development

```bash
uv sync --locked --dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

GitHub Actions runs these checks on Linux, macOS, and Windows with the oldest and newest supported Python versions.

## License

Released under the [MIT License](LICENSE).
