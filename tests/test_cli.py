import os
from unittest.mock import Mock, patch

from main import EXIT_FATAL, EXIT_OK, EXIT_PARTIAL, main


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
