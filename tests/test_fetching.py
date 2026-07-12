import time

import pytest
import requests

from main import (
    DEFAULT_RETRY_BACKOFF_SECONDS,
    DEFAULT_RETRY_COUNT,
    RETRYABLE_STATUS_CODES,
    build_session,
    fetch_all_series_language_data,
    get_episode_files,
    get_episodes,
    get_series,
    positive_worker_count,
)


def test_build_session_retries_transient_get_requests_only():
    session = build_session("api-key")

    for prefix in ("https://", "http://"):
        retry_policy = session.adapters[prefix].max_retries
        assert retry_policy.total == DEFAULT_RETRY_COUNT
        assert retry_policy.connect == DEFAULT_RETRY_COUNT
        assert retry_policy.read == DEFAULT_RETRY_COUNT
        assert retry_policy.status == DEFAULT_RETRY_COUNT
        assert retry_policy.other == 0
        assert retry_policy.allowed_methods == frozenset({"GET"})
        assert retry_policy.status_forcelist == RETRYABLE_STATUS_CODES
        assert retry_policy.backoff_factor == DEFAULT_RETRY_BACKOFF_SECONDS
        assert retry_policy.respect_retry_after_header is True


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


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"records": []}, "expected a list"),
        (["not-an-object"], "index 0: expected an object"),
        ([{"episodeFileId": 1}], "missing seasonNumber"),
    ],
)
def test_get_episodes_rejects_payload_drift(payload, message):
    class InvalidEpisodeSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse(payload)

    with pytest.raises(ValueError, match=message):
        get_episodes(
            InvalidEpisodeSession(),
            42,
            "https://sonarr.example.org/api/v3",
            (3.0, 20.0),
        )


def test_get_episodes_accepts_episode_without_downloaded_file():
    class EpisodeWithoutFileSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse([{"seasonNumber": 1}])

    assert get_episodes(
        EpisodeWithoutFileSession(),
        42,
        "https://sonarr.example.org/api/v3",
        (3.0, 20.0),
    ) == [{"seasonNumber": 1}]


def test_get_episodes_rejects_non_hashable_episode_file_id():
    class InvalidEpisodeSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse([{"seasonNumber": 1, "episodeFileId": [101]}])

    with pytest.raises(ValueError, match="episodeFileId must be a scalar value"):
        get_episodes(
            InvalidEpisodeSession(),
            42,
            "https://sonarr.example.org/api/v3",
            (3.0, 20.0),
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"records": []}, "expected a list"),
        (["not-an-object"], "index 0: expected an object"),
        ([{"mediaInfo": {}}], "missing id"),
        ([{"id": 1, "mediaInfo": []}], "mediaInfo must be an object"),
    ],
)
def test_get_episode_files_rejects_payload_drift(payload, message):
    class InvalidEpisodeFileSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse(payload)

    with pytest.raises(ValueError, match=message):
        get_episode_files(
            InvalidEpisodeFileSession(),
            42,
            "https://sonarr.example.org/api/v3",
            (3.0, 20.0),
        )


def test_get_episode_files_normalizes_null_media_info():
    class NullMediaInfoSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse([{"id": 101, "mediaInfo": None}])

    assert get_episode_files(
        NullMediaInfoSession(),
        42,
        "https://sonarr.example.org/api/v3",
        (3.0, 20.0),
    ) == {101: {"id": 101, "mediaInfo": {}}}


def test_get_episode_files_rejects_non_hashable_id():
    class InvalidEpisodeFileSession:
        def get(self, _url, timeout):
            assert timeout == (3.0, 20.0)
            return FakeResponse([{"id": [101], "mediaInfo": {}}])

    with pytest.raises(ValueError, match="id must be a scalar value"):
        get_episode_files(
            InvalidEpisodeFileSession(),
            42,
            "https://sonarr.example.org/api/v3",
            (3.0, 20.0),
        )
