from collections import defaultdict

from main import (
    analyze_language_distribution,
    detect_mismatches,
    detect_wanted_coverage,
    normalize_audio_languages,
    normalize_url,
    parse_wanted_langs,
)


def test_normalize_audio_languages_aliases_order_and_duplicates():
    assert normalize_audio_languages(" Italian / ENG / it ") == "eng/ita"
    assert normalize_audio_languages("unknown") == "und"
    assert normalize_audio_languages("") == "und"


def test_parse_wanted_languages_preserves_first_seen_order():
    assert parse_wanted_langs("it, ENG/ita,fr") == ["ita", "eng", "fra"]


def test_normalize_url_accepts_base_and_api_url():
    assert normalize_url("https://sonarr.example.org/") == "https://sonarr.example.org/api/v3"
    assert normalize_url("https://sonarr.example.org/api/v3") == "https://sonarr.example.org/api/v3"


def test_analyze_language_distribution_counts_files_and_unknown_metadata():
    series = {"title": "Example"}
    episodes = [
        {"seasonNumber": 1, "episodeFileId": 10},
        {"seasonNumber": 1, "episodeFileId": 11},
        {"seasonNumber": 1, "episodeFileId": 0},
    ]
    files = {
        10: {"mediaInfo": {"audioLanguages": "ita/eng"}},
        11: {},
    }

    result = analyze_language_distribution(series, episodes, files)

    assert dict(result["Example"][1]) == {"eng/ita": 1, "und": 1}


def test_mismatch_output_is_deterministic():
    summary = {
        "Zulu": {2: {"ita": 1, "eng": 2}, 1: {"ita": 3}},
        "alpha": {1: {"und": 1, "ita": 1}},
    }

    result = detect_mismatches(summary)

    assert [(item["serie"], item.get("stagione"), item["type"]) for item in result] == [
        ("alpha", 1, "stagione_mista"),
        ("alpha", None, "serie_mista"),
        ("Zulu", 2, "stagione_mista"),
        ("Zulu", None, "serie_mista"),
    ]
    assert result[0]["lingue"] == {"ita": 1, "und": 1}
    assert result[-1]["lingue"] == ["eng", "ita"]


def test_wanted_coverage_ignores_unknown_and_sorts_wanted_languages():
    summary = defaultdict(dict)
    summary["Example"][1] = {"und": 2, "eng": 1, "ita": 1}

    result = detect_wanted_coverage(
        summary,
        ["ita", "eng"],
        include_all=True,
        ignore_unknown=True,
    )

    assert result == [
        {
            "type": "stagione_supportata",
            "serie": "Example",
            "stagione": 1,
            "totale": 2,
            "supportati": 2,
            "lingue_desiderate": ["eng", "ita"],
        }
    ]
