# sonarr-lang-checker

English · [Italiano](README.it.md)

[![CI](https://github.com/alsd4git/sonarr-lang-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/alsd4git/sonarr-lang-checker/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Find inconsistent audio-language coverage in a Sonarr v4 library. The CLI reports mixed-language seasons, compares seasons within a series, and checks whether episodes contain a requested set of languages.

Sonarr v4 is required. Earlier versions are not supported.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)
- A Sonarr v4 URL and API key

## Installation

Install a tagged version directly from GitHub:

```bash
uv tool install git+https://github.com/alsd4git/sonarr-lang-checker.git@v0.1.0
sonarr-lang-checker --help
```

For a one-off run without keeping the tool installed:

```bash
uvx --from git+https://github.com/alsd4git/sonarr-lang-checker.git@v0.1.0 sonarr-lang-checker --help
```

The examples are intentionally pinned to a tag. Tagged GitHub Releases also publish wheel and source distributions, so a release asset can be used as an alternative reproducible installation source.

## Configuration

Create `.env` in the directory where you run the command:

```dotenv
API_KEY=replace-with-your-api-key
SONARR_URL=https://sonarr.example.org
```

Keep `.env` private. API keys passed as command-line arguments may be recorded in shell history or process listings.

## Usage

```bash
# Standard scan
sonarr-lang-checker

# Print JSON to stdout
sonarr-lang-checker --json

# Save structured results, including partial-failure metadata
sonarr-lang-checker --structured-json --output report.json

# Report missing or partial Italian and English coverage
sonarr-lang-checker --wanted-langs ita,eng

# Include seasons that fully match the requested languages
sonarr-lang-checker --wanted-langs ita,eng --show-all

# Reduce concurrent Sonarr requests
sonarr-lang-checker --workers 2
```

Use `sonarr-lang-checker --help` for the complete option list.

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
git clone https://github.com/alsd4git/sonarr-lang-checker.git
cd sonarr-lang-checker
uv sync --locked --dev
uv run sonarr-lang-checker --help
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv build
```

`main.py` remains directly executable for compatibility, but the installed `sonarr-lang-checker` entry point is the preferred user-facing interface.

GitHub Actions runs checks on Linux, macOS, and Windows with the oldest and newest supported Python versions.

## License

Released under the [MIT License](LICENSE).
