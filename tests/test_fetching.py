import time

import pytest
import requests

from main import fetch_all_series_language_data, get_series, positive_worker_count


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def get(self, url, timeout):
        assert timeout == (3.0, 20.0)
        if "seriesId=2" in url:
            raise requests.Timeout("Sonarr did not answer")
        if "/episode?" in url:
            return FakeResponse([{"seasonNumber": 1, "episodeFileId": 101}])
        if "/episodefile?" in url:
            return FakeResponse(
                [{"id": 101, "mediaInfo": {"audioLanguages": "ita"}}]
            )
        raise AssertionError(f"Unexpected URL: {url}")

    def close(self):
        return None


def test_concurrent_fetch_returns_sorted_data_and_partial_failures():
    series = [
        {"id": 2, "title": "Zulu"},
        {"id": 1, "title": "alpha"},
    ]

    data, failures = fetch_all_series_language_data(
        series,
        FakeSession,
        "https://sonarr.example.org/api/v3",
        (3.0, 20.0),
        workers=2,
    )

    assert list(data) == ["alpha"]
    assert dict(data["alpha"][1]) == {"ita": 1}
    assert failures == [{"serie": "Zulu", "errore": "Sonarr did not answer"}]


def test_worker_count_is_bounded():
    assert positive_worker_count("1") == 1
    assert positive_worker_count("16") == 16


def test_same_title_series_are_kept_and_deterministic():
    class DuplicateTitleSession(FakeSession):
        def get(self, url, timeout):
            if "seriesId=2" in url:
                time.sleep(0.01)
            if "/episode?" in url:
                series_id = 2 if "seriesId=2" in url else 1
                return FakeResponse([{"seasonNumber": 1, "episodeFileId": series_id}])
            if "/episodefile?" in url:
                series_id = 2 if "seriesId=2" in url else 1
                return FakeResponse(
                    [{"id": series_id, "mediaInfo": {"audioLanguages": "ita"}}]
                )
            raise AssertionError(f"Unexpected URL: {url}")

    data, failures = fetch_all_series_language_data(
        [
            {"id": 2, "title": "Same", "year": 2024},
            {"id": 1, "title": "Same", "year": 2020},
        ],
        DuplicateTitleSession,
        "https://sonarr.example.org/api/v3",
        (3.0, 20.0),
        workers=2,
    )

    assert list(data) == ["Same (2020, ID 1)", "Same (2024, ID 2)"]
    assert failures == []


def test_session_factory_failure_becomes_partial_result():
    data, failures = fetch_all_series_language_data(
        [{"id": 1, "title": "Broken"}],
        lambda: (_ for _ in ()).throw(RuntimeError("session failed")),
        "https://sonarr.example.org/api/v3",
        (3.0, 20.0),
        workers=1,
    )

    assert data == {}
    assert failures == [{"serie": "Broken", "errore": "session failed"}]


def test_get_series_rejects_invalid_payload():
    class InvalidSeriesSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse({"unexpected": "object"})

    with pytest.raises(ValueError, match="invalid payload"):
        get_series(
            InvalidSeriesSession(),
            "https://sonarr.example.org/api/v3",
            (3.0, 20.0),
        )
