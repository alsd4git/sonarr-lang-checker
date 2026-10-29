"""Render an offline, synthetic run of the Sonarr language checker as SVG."""

from __future__ import annotations

import argparse
import contextlib
import html
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402


SERIES = [
    {"id": 1, "title": "Sample Series", "year": 2024, "seriesType": "standard"},
    {"id": 2, "title": "Another Example", "year": 2023, "seriesType": "standard"},
]
EPISODES = {
    1: [
        {"seasonNumber": 1, "episodeFileId": 101},
        {"seasonNumber": 1, "episodeFileId": 102},
        {"seasonNumber": 2, "episodeFileId": 103},
    ],
    2: [
        {"seasonNumber": 1, "episodeFileId": 201},
        {"seasonNumber": 1, "episodeFileId": 202},
    ],
}
FILES = {
    1: {
        101: {"id": 101, "mediaInfo": {"audioLanguages": "ita"}},
        102: {"id": 102, "mediaInfo": {"audioLanguages": "eng"}},
        103: {"id": 103, "mediaInfo": {"audioLanguages": "eng"}},
    },
    2: {
        201: {"id": 201, "mediaInfo": {"audioLanguages": "ita"}},
        202: {"id": 202, "mediaInfo": {"audioLanguages": "ita"}},
    },
}


def build_language_data(series_list, _session_factory, _base_url, _timeout, _workers):
    """Return analysis of fixture episodes without constructing an HTTP request."""
    result = {}
    for series in series_list:
        title = series["title"]
        summary = main.analyze_language_distribution(series, EPISODES[series["id"]], FILES[series["id"]])
        result[title] = summary[title]
    return result, []


def capture_demo_output() -> str:
    stdout = io.StringIO()
    stderr = io.StringIO()
    previous_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="sonarr-lang-checker-demo-") as temporary_directory:
        os.chdir(temporary_directory)
        try:
            with (
                patch.object(main, "get_series", return_value=SERIES),
                patch.object(main, "fetch_all_series_language_data", side_effect=build_language_data),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                exit_code = main.main(
                    [
                        "--apikey",
                        "synthetic-demo-key",
                        "--url",
                        "https://sonarr.example.invalid",
                        "--show-all",
                    ]
                )
        finally:
            os.chdir(previous_directory)

    if exit_code != main.EXIT_OK or stderr.getvalue():
        raise RuntimeError(f"Synthetic CLI run failed (exit {exit_code}): {stderr.getvalue()}")
    return stdout.getvalue().rstrip()


def render_svg(output: str) -> str:
    lines = output.splitlines()
    padding = 36
    line_height = 27
    header_height = 88
    width = 1180
    height = header_height + padding + max(1, len(lines)) * line_height + padding
    rendered_lines = "\n".join(
        f'<text x="{padding}" y="{header_height + index * line_height}" xml:space="preserve">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
  <title id="title">Sonarr language checker synthetic demo</title>
  <desc id="description">Terminal output from the real CLI using synthetic library data. No Sonarr server was contacted.</desc>
  <rect width="100%" height="100%" rx="14" fill="#111827"/>
  <rect width="100%" height="54" rx="14" fill="#1f2937"/>
  <circle cx="25" cy="27" r="7" fill="#f87171"/>
  <circle cx="49" cy="27" r="7" fill="#fbbf24"/>
  <circle cx="73" cy="27" r="7" fill="#34d399"/>
  <text x="102" y="33" class="chrome">sonarr-lang-checker · synthetic demo</text>
  <text x="{padding}" y="75" class="notice">SYNTHETIC DATA ONLY · NO REQUESTS SENT</text>
  <g class="terminal">{rendered_lines}</g>
  <style>
    .chrome {{ fill: #d1d5db; font: 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .notice {{ fill: #6ee7b7; font: 700 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 1px; }}
    .terminal {{ fill: #f3f4f6; font: 15px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  </style>
</svg>
'''


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "demo-output.svg",
        help="SVG destination (default: docs/demo-output.svg)",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(capture_demo_output()), encoding="utf-8")
    print(f"Wrote synthetic CLI demo to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
