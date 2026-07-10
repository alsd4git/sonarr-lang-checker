import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import getenv
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import requests
from dotenv import load_dotenv

from language_flags import LANGUAGE_FLAGS

PADDING_WIDTH = 24  # larghezza usata per allineare le etichette nella stampa
DEFAULT_CONNECT_TIMEOUT = 3.0
DEFAULT_READ_TIMEOUT = 20.0
DEFAULT_WORKERS = 4
MAX_WORKERS = 16
EXIT_OK = 0
EXIT_FATAL = 1
EXIT_PARTIAL = 2

# Carica .env se presente
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def positive_worker_count(value: str) -> int:
    workers = int(value)
    if not 1 <= workers <= MAX_WORKERS:
        raise argparse.ArgumentTypeError(
            f"deve essere compreso tra 1 e {MAX_WORKERS}"
        )
    return workers


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Controlla le discrepanze linguistiche nelle stagioni/serie presenti in Sonarr (compatibile solo con Sonarr v4)."
    )
    parser.add_argument('--apikey', default=getenv("API_KEY"), help='API key di Sonarr (può anche essere in .env)')
    parser.add_argument('--url', default=getenv("SONARR_URL"), help='URL base di Sonarr (può anche essere in .env)')
    parser.add_argument('--output', help='Percorso file su cui salvare l’output')
    parser.add_argument('--json', action='store_true', help='Mostra output in formato JSON')
    parser.add_argument('--show-all', action='store_true', help='Mostra anche stagioni monolingua')
    parser.add_argument('--ignore-unknown', action='store_true', help='Ignora "und/unknown" nel calcolo dei mismatch')
    parser.add_argument('--timeout', type=float, help='Timeout HTTP in secondi (solo lettura). Connessione fissa a 3s')
    parser.add_argument('--wanted-langs', dest='wanted_langs', help='Lista di lingue desiderate separate da virgola (es: ita,eng)')
    parser.add_argument('--wanted-lang', dest='wanted_langs', help='Alias di --wanted-langs')
    parser.add_argument('--ignore-anime', action='store_true', help='Ignora le serie con tipo "Anime"')
    parser.add_argument(
        '--workers',
        type=positive_worker_count,
        default=DEFAULT_WORKERS,
        help=f'Richieste concorrenti massime verso Sonarr (default: {DEFAULT_WORKERS}, max: {MAX_WORKERS})',
    )
    return parser.parse_args(argv)


def normalize_url(base_url: str) -> str:
    base_url = base_url.rstrip('/')
    if not base_url.endswith("/api/v3"):
        base_url += "/api/v3"
    return base_url


def get_series(session: requests.Session, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/series', timeout=timeout)
    res.raise_for_status()
    payload = res.json()
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Sonarr /series returned an invalid payload")
    return payload

def get_episodes(session: requests.Session, series_id: int, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/episode?seriesId={series_id}', timeout=timeout)
    res.raise_for_status()
    return res.json()

def get_episode_files(session: requests.Session, series_id: int, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/episodefile?seriesId={series_id}', timeout=timeout)
    res.raise_for_status()
    files = res.json()
    return {file["id"]: file for file in files}


def build_session(apikey: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({'X-Api-Key': apikey})
    return session


def get_flag(lang_code: str) -> str:
    parts = lang_code.lower().split('/')
    return ' '.join(LANGUAGE_FLAGS.get(code, '🏳️') for code in parts)

def normalize_audio_languages(value: str) -> str:
    """
    Normalize Sonarr mediaInfo.audioLanguages values so that order does not matter.
    Examples:
    - "ita/eng" == "eng/ita" -> "eng/ita"
    - Handles extra spaces and casing: "ENG / Ita" -> "eng/ita"
    Keeps tokens as-is beyond lowercasing; does not attempt synonym mapping (e.g., en->eng).
    """
    if not value:
        return "und"
    # Lowercase and split on '/'; trim spaces; drop empties; deduplicate while sorting
    tokens: List[str] = [t.strip() for t in str(value).lower().split('/') if t.strip()]
    if not tokens:
        return "und"
    # Map common synonyms/aliases
    alias = {
        'en': 'eng', 'english': 'eng',
        'it': 'ita', 'italian': 'ita',
        'ja': 'jpn', 'jp': 'jpn', 'japanese': 'jpn',
        'fr': 'fra', 'fre': 'fra', 'french': 'fra',
        'de': 'deu', 'ger': 'deu', 'german': 'deu',
        'pt': 'por', 'portuguese': 'por',
        'ru': 'rus', 'russian': 'rus',
        'zh': 'zho', 'chi': 'zho', 'chinese': 'zho',
        'es': 'spa', 'spanish': 'spa',
        'unknown': 'und', 'undetermined': 'und', 'unk': 'und', 'und': 'und',
    }
    mapped = [alias.get(t, t) for t in tokens]
    # Remove duplicates, then sort for order-insensitivity
    unique = sorted(set(mapped))
    return "/".join(unique)


def parse_wanted_langs(csv: str) -> List[str]:
    if not csv:
        return []
    items = []
    for part in csv.split(','):
        token = normalize_audio_languages(part)
        # normalize_audio_languages may return combined values if input had '/'
        items.extend([t for t in token.split('/') if t])
    # deduplicate while preserving order
    seen = set()
    result = []
    for t in items:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def analyze_language_distribution(series, episodes, files_by_id):
    lang_summary = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for ep in episodes:
        ep_file_id = ep.get("episodeFileId")
        if not ep_file_id:
            continue
        file = files_by_id.get(ep_file_id, {})
        raw_lang = file.get("mediaInfo", {}).get("audioLanguages", "und")
        lang = normalize_audio_languages(raw_lang)
        season = ep["seasonNumber"]
        lang_summary[series["title"]][season][lang] += 1
    return lang_summary


def _fetch_series_language_data(
    serie: dict,
    session_factory: Callable[[], requests.Session],
    base_url: str,
    timeout: Tuple[float, float],
):
    """Fetch and analyze one series using a worker-local HTTP session."""
    title = str(serie.get("title", f"ID {serie.get('id', 'sconosciuto')}"))
    series_id = serie.get("id")
    session = None
    try:
        if series_id is None:
            raise ValueError("series id is missing")
        session = session_factory()
        episodes = get_episodes(session, series_id, base_url, timeout)
        files_by_id = get_episode_files(session, series_id, base_url, timeout)
        lang_data = analyze_language_distribution(serie, episodes, files_by_id)
        return series_id, title, serie.get("year"), lang_data.get(title, {}), None
    except (requests.RequestException, KeyError, TypeError, ValueError, RuntimeError) as exc:
        return series_id, title, serie.get("year"), {}, str(exc)
    finally:
        if session is not None:
            session.close()


def fetch_all_series_language_data(
    series_list: List[dict],
    session_factory: Callable[[], requests.Session],
    base_url: str,
    timeout: Tuple[float, float],
    workers: int,
):
    """Fetch series concurrently and merge results in deterministic title order."""
    fetched = []
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _fetch_series_language_data,
                serie,
                session_factory,
                base_url,
                timeout,
            ): str(serie.get("title", f"ID {serie.get('id', 'sconosciuto')}"))
            for serie in series_list
        }
        for future in as_completed(futures):
            fallback_title = futures[future]
            try:
                series_id, title, year, seasons, error = future.result()
            except Exception as exc:  # Protect a partial scan from one failed worker.
                failures.append({"serie": fallback_title, "errore": str(exc)})
                continue
            if error is None:
                fetched.append((title.casefold(), title, str(series_id), year, seasons))
            else:
                failures.append({"serie": title, "errore": error})

    all_lang_data: Dict[str, dict] = {}
    title_counts = defaultdict(int)
    for _, title, _, _, _ in fetched:
        title_counts[title.casefold()] += 1
    for _, title, series_id, year, seasons in sorted(
        fetched, key=lambda item: (item[0], item[1], item[2])
    ):
        display_title = title
        if title_counts[title.casefold()] > 1:
            qualifier = (
                f"{year}, ID {series_id}"
                if year not in (None, "")
                else f"ID {series_id}"
            )
            display_title = f"{title} ({qualifier})"
        all_lang_data[display_title] = seasons
    failures.sort(key=lambda item: (item["serie"].casefold(), item["serie"]))
    return all_lang_data, failures


def detect_wanted_coverage(lang_summary, wanted: List[str], include_all=False, ignore_unknown=False):
    issues = []
    if not wanted:
        return issues
    wanted_set = set(wanted)
    wanted_sorted = sorted(wanted_set)
    for serie in sorted(lang_summary, key=lambda value: (value.casefold(), value)):
        seasons = lang_summary[serie]
        for season_num in sorted(seasons):
            langs = seasons[season_num]
            # Optionally drop unknowns from consideration
            if ignore_unknown:
                langs = {k: v for k, v in langs.items() if k != 'und'}
            total = sum(langs.values())
            supported = 0
            for combo, count in langs.items():
                tokens = combo.split('/')
                if any(t in wanted_set for t in tokens):
                    supported += count
            if total == 0:
                # nothing to evaluate after ignoring unknowns
                continue
            if supported == 0:
                issues.append({
                    "type": "stagione_non_supportata",
                    "serie": serie,
                    "stagione": season_num,
                    "totale": total,
                    "supportati": supported,
                    "lingue_desiderate": wanted_sorted
                })
            elif supported == total:
                if include_all:
                    issues.append({
                        "type": "stagione_supportata",
                        "serie": serie,
                        "stagione": season_num,
                        "totale": total,
                        "supportati": supported,
                        "lingue_desiderate": wanted_sorted
                    })
            else:
                issues.append({
                    "type": "stagione_parzialmente_supportata",
                    "serie": serie,
                    "stagione": season_num,
                    "totale": total,
                    "supportati": supported,
                    "lingue_desiderate": wanted_sorted
                })
    return issues


def detect_mismatches(lang_summary, include_all=False, ignore_unknown=False):
    issues = []
    for serie in sorted(lang_summary, key=lambda value: (value.casefold(), value)):
        seasons = lang_summary[serie]
        series_langs = set()
        for season_num in sorted(seasons):
            langs = seasons[season_num]
            sorted_langs = dict(sorted(langs.items()))
            if ignore_unknown:
                known_langs = {k: v for k, v in langs.items() if k != 'und'}
                mixed = len(known_langs) > 1
            else:
                mixed = len(langs) > 1
            if mixed:
                issues.append({
                    "type": "stagione_mista",
                    "serie": serie,
                    "stagione": season_num,
                    "lingue": sorted_langs
                })
            elif include_all:
                lang = next(iter(sorted_langs))
                issues.append({
                    "type": "stagione_ok",
                    "serie": serie,
                    "stagione": season_num,
                    "lingue": {lang: langs[lang]}
                })
            if ignore_unknown:
                series_langs.update({k for k in langs.keys() if k != 'und'})
            else:
                series_langs.update(langs.keys())

        if len(series_langs) > 1:
            issues.append({
                "type": "serie_mista",
                "serie": serie,
                "lingue": sorted(series_langs)
            })
        else:
            if include_all:
                issues.append({
                    "type": "serie_ok",
                    "serie": serie,
                    "lingue": sorted(series_langs)
                })
    return issues


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.apikey or not args.url:
        print("❌ Devi specificare sia l'API Key che l'URL base (via CLI o .env)")
        return EXIT_FATAL

    # Prepare HTTP session and timeouts
    session = build_session(args.apikey)
    timeout = (
        DEFAULT_CONNECT_TIMEOUT,
        args.timeout if args.timeout and args.timeout > 0 else DEFAULT_READ_TIMEOUT,
    )
    base_url = normalize_url(args.url)

    print(f"📡 Recupero dati da Sonarr @ {base_url} ...")
    try:
        series_list = get_series(session, base_url, timeout)
    except (requests.RequestException, ValueError) as e:
        print(f"❌ Errore nella connessione a Sonarr: {e}")
        return EXIT_FATAL
    finally:
        session.close()

    print("📦 Analisi episodi in corso...")
    selected_series = [
        serie
        for serie in series_list
        if not (
            args.ignore_anime
            and str(serie.get('seriesType', '')).lower() == 'anime'
        )
    ]
    all_lang_data, failures = fetch_all_series_language_data(
        selected_series,
        lambda: build_session(args.apikey),
        base_url,
        timeout,
        args.workers,
    )
    for failure in failures:
        print(
            f"⚠️ Errore durante l'elaborazione della serie "
            f"'{failure['serie']}': {failure['errore']}",
            file=sys.stderr,
        )

    wanted_list = parse_wanted_langs(args.wanted_langs) if args.wanted_langs else []
    if wanted_list:
        results = detect_wanted_coverage(all_lang_data, wanted_list, include_all=args.show_all, ignore_unknown=args.ignore_unknown)
    else:
        results = detect_mismatches(all_lang_data, include_all=args.show_all, ignore_unknown=args.ignore_unknown)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Risultati salvati in: {args.output}")
    elif args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("\n📊 Risultati:")
        if results:
            last_serie = None
            for item in results:
                if last_serie and item['serie'] != last_serie:
                    print()
                last_serie = item['serie']

                label = None
                pad = 24
                if item["type"] == "stagione_mista":
                    # nota: abbiamo due spazi con "⚠️" per la stampa corretta nel terminale in uso, valutiamo se cambiare
                    label = "⚠️  STAGIONE MISTA"
                    pad = PADDING_WIDTH
                elif item["type"] == "stagione_ok":
                    label = "✅ STAGIONE OK"
                    pad = PADDING_WIDTH - 2
                elif item["type"] == "serie_mista":
                    # nota: abbiamo due spazi con "⚠️" per la stampa corretta nel terminale in uso, valutiamo se cambiare
                    label = "⚠️  SERIE MISTA"
                    pad = PADDING_WIDTH
                elif item["type"] == "serie_ok":
                    label = "✅ SERIE OK"
                    pad = PADDING_WIDTH - 2
                if item["type"] in ("stagione_mista", "stagione_ok"):
                    lang_display = {f"{get_flag(k)} {k}": v for k, v in item['lingue'].items()}
                    print(f"  [{label}]".ljust(pad) + f" {item['serie']} - Stagione {item['stagione']}: {lang_display}")
                elif item["type"] == "serie_mista":
                    langs = ', '.join(f"{get_flag(k)} {k}" for k in item['lingue'])
                    print(f"  [{label}]".ljust(pad) + f" {item['serie']}: Lingue usate: [{langs}]")
                elif item["type"] == "serie_ok":
                    langs = ', '.join(f"{get_flag(k)} {k}" for k in item['lingue'])
                    print(f"  [{label}]".ljust(pad) + f" {item['serie']}: Lingua unica: [{langs}]")
                elif item["type"] in ("stagione_non_supportata", "stagione_parzialmente_supportata", "stagione_supportata"):
                    if item["type"] == "stagione_non_supportata":
                        label = "🚫 NESSUNA LINGUA DESIDERATA"
                        pad = PADDING_WIDTH - 1
                    elif item["type"] == "stagione_parzialmente_supportata":
                        label = "🟡 PARZIALMENTE SUPPORTATA"
                        pad = PADDING_WIDTH
                    elif item["type"] == "stagione_supportata":
                        label = "✅ STAGIONE OK (desiderata)"
                        pad = PADDING_WIDTH - 2
                    wanted_disp = ', '.join(f"{get_flag(k)} {k}" for k in item['lingue_desiderate'])
                    print(
                        f"  [{label}]".ljust(pad)
                        + f" {item['serie']} - Stagione {item['stagione']}: "
                        + f"{item['supportati']}/{item['totale']} episodi con lingue desiderate [{wanted_disp}]"
                    )
        else:
            print("    ✅ Nessuna discrepanza linguistica rilevata.")

    if failures:
        succeeded = len(selected_series) - len(failures)
        print(
            f"⚠️ Analisi incompleta: {succeeded}/{len(selected_series)} serie "
            f"analizzate, {len(failures)} non riuscite. Exit code {EXIT_PARTIAL}.",
            file=sys.stderr,
        )
        return EXIT_PARTIAL

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
