import argparse
import requests
import sys
import json
from collections import defaultdict
from os import getenv
from pathlib import Path
from dotenv import load_dotenv
from language_flags import LANGUAGE_FLAGS

PADDING_WIDTH = 24  # larghezza usata per allineare le etichette nella stampa

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
    return parser.parse_args()


def normalize_url(base_url: str) -> str:
    base_url = base_url.rstrip('/')
    if not base_url.endswith("/api/v3"):
        base_url += "/api/v3"
    return base_url


def get_series(base_url, headers):
    res = requests.get(f'{base_url}/series', headers=headers)
    res.raise_for_status()
    return res.json()


def get_episodes(series_id, base_url, headers):
    res = requests.get(f'{base_url}/episode?seriesId={series_id}', headers=headers)
    res.raise_for_status()
    return res.json()


def get_episode_files(series_id, base_url, headers):
    res = requests.get(f'{base_url}/episodefile?seriesId={series_id}', headers=headers)
    res.raise_for_status()
    files = res.json()
    return {file["id"]: file for file in files}


def get_flag(lang_code: str) -> str:
    parts = lang_code.lower().split('/')
    return ' '.join(LANGUAGE_FLAGS.get(code, '🏳️') for code in parts)


def analyze_language_distribution(series, episodes, files_by_id):
    lang_summary = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for ep in episodes:
        ep_file_id = ep.get("episodeFileId")
        if not ep_file_id:
            continue
        file = files_by_id.get(ep_file_id, {})
        lang = file.get("mediaInfo", {}).get("audioLanguages", "Unknown")
        season = ep["seasonNumber"]
        lang_summary[series["title"]][season][lang] += 1
    return lang_summary


def detect_mismatches(lang_summary, include_all=False):
    issues = []
    for serie, seasons in lang_summary.items():
        series_langs = set()
        for season_num, langs in seasons.items():
            if len(langs) > 1:
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

    headers = {'X-Api-Key': args.apikey}
    base_url = normalize_url(args.url)

    print(f"📡 Recupero dati da Sonarr @ {base_url} ...")
    try:
        series_list = get_series(base_url, headers)
    except requests.RequestException as e:
        print(f"❌ Errore nella connessione a Sonarr: {e}")
        sys.exit(1)

    print("📦 Analisi episodi in corso...")
    all_lang_data = {}

    for serie in series_list:
        try:
            episodes = get_episodes(serie["id"], base_url, headers)
            serie_files = get_episode_files(serie["id"], base_url, headers)
            lang_data = analyze_language_distribution(serie, episodes, serie_files)
            all_lang_data.update(lang_data)
        except requests.RequestException as e:
            print(f"⚠️ Errore durante l'elaborazione della serie '{serie['title']}': {e}")

    results = detect_mismatches(all_lang_data, include_all=args.show_all)

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
