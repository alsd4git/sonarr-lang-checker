import json
import os
from unittest.mock import Mock, patch

import pytest

from main import EXIT_FATAL, EXIT_OK, EXIT_PARTIAL, main, parse_args


@patch("main.fetch_all_series_language_data")
@patch("main.get_series")
@patch("main.build_session")
def test_main_returns_partial_exit_code_and_summary(
    build_session, get_series, fetch_all, capsys
):
    build_session.return_value = Mock()
    get_series.return_value = [
        {"id": 1, "title": "OK"},
        {"id": 2, "title": "Broken"},
    ]
    fetch_all.return_value = ({}, [{"serie": "Broken", "errore": "timeout"}])

    exit_code = main(["--apikey", "secret", "--url", "https://sonarr", "--json"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_PARTIAL
    assert "Analisi incompleta: 1/2" in captured.err
    assert "'Broken': timeout" in captured.err


@patch("main.fetch_all_series_language_data", return_value=({}, []))
@patch("main.get_series", return_value=[])
@patch("main.build_session")
def test_main_returns_success_for_complete_analysis(
    build_session, _get_series, _fetch_all
):
    build_session.return_value = Mock()
    assert main(["--apikey", "secret", "--url", "https://sonarr", "--json"]) == EXIT_OK


def test_main_returns_fatal_without_configuration():
    with patch.dict(os.environ, {}, clear=True):
        assert main([]) == EXIT_FATAL


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_timeout_must_be_positive_and_finite(value):
    with pytest.raises(SystemExit) as error:
        parse_args(["--timeout", value])

    assert error.value.code == 2


@patch("main.fetch_all_series_language_data")
@patch("main.get_series")
@patch("main.build_session")
def test_structured_output_includes_partial_metadata(
    build_session, get_series, fetch_all, tmp_path
):
    build_session.return_value = Mock()
    get_series.return_value = [
        {"id": 1, "title": "OK"},
        {"id": 2, "title": "Broken"},
    ]
    fetch_all.return_value = (
        {"OK": {1: {"ita": 1}}},
        [{"serie": "Broken", "errore": "payload drift"}],
    )
    output = tmp_path / "report.json"

    exit_code = main(
        [
            "--apikey",
            "secret",
            "--url",
            "https://sonarr",
            "--structured-json",
            "--output",
            str(output),
        ]
    )

    assert exit_code == EXIT_PARTIAL
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == {
        "results": [],
        "failures": [{"serie": "Broken", "errore": "payload drift"}],
        "complete": False,
    }


@patch("main.fetch_all_series_language_data", return_value=({}, []))
@patch("main.get_series", return_value=[])
@patch("main.build_session")
def test_legacy_output_file_keeps_results_list_shape(
    build_session, _get_series, _fetch_all, tmp_path
):
    build_session.return_value = Mock()
    output = tmp_path / "results.json"

    assert (
        main(
            [
                "--apikey",
                "secret",
                "--url",
                "https://sonarr",
                "--output",
                str(output),
            ]
        )
        == EXIT_OK
    )
    assert json.loads(output.read_text(encoding="utf-8")) == []
