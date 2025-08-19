import argparse
import requests
import sys
import json
from collections import defaultdict
from os import getenv
from pathlib import Path
from dotenv import load_dotenv
from language_flags import LANGUAGE_FLAGS
from typing import List, Tuple

PADDING_WIDTH = 24  # larghezza usata per allineare le etichette nella stampa
DEFAULT_CONNECT_TIMEOUT = 3.0
DEFAULT_READ_TIMEOUT = 20.0

# Carica .env se presente
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def parse_args():
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
    return parser.parse_args()


def normalize_url(base_url: str) -> str:
    base_url = base_url.rstrip('/')
    if not base_url.endswith("/api/v3"):
        base_url += "/api/v3"
    return base_url


def get_series(session: requests.Session, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/series', timeout=timeout)
    res.raise_for_status()
    return res.json()

def get_episodes(session: requests.Session, series_id: int, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/episode?seriesId={series_id}', timeout=timeout)
    res.raise_for_status()
    return res.json()

def get_episode_files(session: requests.Session, series_id: int, base_url: str, timeout: Tuple[float, float]):
    res = session.get(f'{base_url}/episodefile?seriesId={series_id}', timeout=timeout)
    res.raise_for_status()
    files = res.json()
    return {file["id"]: file for file in files}


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


def detect_mismatches(lang_summary, include_all=False, ignore_unknown=False):
    issues = []
    for serie, seasons in lang_summary.items():
        series_langs = set()
        for season_num, langs in seasons.items():
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
                    "lingue": dict(langs)
                })
            elif include_all:
                lang = next(iter(langs.keys()))
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
                "lingue": list(series_langs)
            })
        else:
            if include_all:
                issues.append({
                    "type": "serie_ok",
                    "serie": serie,
                    "lingue": list(series_langs)
                })
    return issues


def main():
    args = parse_args()
    if not args.apikey or not args.url:
        print("❌ Devi specificare sia l'API Key che l'URL base (via CLI o .env)")
        sys.exit(1)

    # Prepare HTTP session and timeouts
    session = requests.Session()
    session.headers.update({'X-Api-Key': args.apikey})
    timeout = (
        DEFAULT_CONNECT_TIMEOUT,
        args.timeout if args.timeout and args.timeout > 0 else DEFAULT_READ_TIMEOUT,
    )
    base_url = normalize_url(args.url)

    print(f"📡 Recupero dati da Sonarr @ {base_url} ...")
    try:
        series_list = get_series(session, base_url, timeout)
    except requests.RequestException as e:
        print(f"❌ Errore nella connessione a Sonarr: {e}")
        sys.exit(1)

    print("📦 Analisi episodi in corso...")
    all_lang_data = {}

    for serie in series_list:
        try:
            episodes = get_episodes(session, serie["id"], base_url, timeout)
            serie_files = get_episode_files(session, serie["id"], base_url, timeout)
            lang_data = analyze_language_distribution(serie, episodes, serie_files)
            all_lang_data.update(lang_data)
        except requests.RequestException as e:
            print(f"⚠️ Errore durante l'elaborazione della serie '{serie['title']}': {e}")

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
        else:
            print("    ✅ Nessuna discrepanza linguistica rilevata.")


if __name__ == "__main__":
    main()
