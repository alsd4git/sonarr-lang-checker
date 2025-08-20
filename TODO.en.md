# 📝 TODO - sonarr-lang-checker

[Italiano](TODO.md) · English

List of upcoming improvements and future ideas for the project.

---

## 🔧 Features

- [x] Normalize `audioLanguages` strings (e.g., `ita/eng` == `eng/ita`)
- [x] `--ignore-unknown` flag to exclude `und` from mismatch decisions
- [x] `--timeout` flag to control HTTP read timeout
- [ ] CSV / Excel export support
- [ ] File logging (e.g., `log/scan.log`)
- [ ] `--filter` option to show only mixed seasons
- [ ] Colored / highlighted CLI output
- [ ] Flag to include only complete series
- [ ] Sort output by severity / number of mismatches
 - [x] Desired language coverage report (`--wanted-langs`)
 - [x] Alias `--wanted-lang`
 - [x] Ignore Anime series (`--ignore-anime`)

---

## 🤖 Automation

- [ ] Cronjob support (`--silent` or `--notify`)
- [ ] `Dockerfile` with preconfigured `uv`
- [ ] Telegram / Email notifications for detected mismatches

---

## 🌐 Interface

- [ ] Interactive CLI (e.g., with `InquirerPy` or `rich.prompt`)
- [ ] Minimal Web UI with Streamlit or Flask
- [ ] "Audit" mode with stats only

---

## 🧹 Cleanup

- [ ] Handle episodes without an associated file
- [ ] Detect duplicate series / aliases
- [ ] Support coherent multi‑language merging

---

## 💡 Extra ideas

- [ ] Radarr integration for movies
- [ ] Offline‑generated HTML report
- [ ] Multi‑profile Sonarr support via YAML config
