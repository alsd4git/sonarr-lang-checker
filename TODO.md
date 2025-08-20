# 📝 TODO - sonarr-lang-checker

Italiano · [English](TODO.en.md)

Elenco dei prossimi miglioramenti e idee future per il progetto.

---

## 🔧 Funzionalità

- [x] Normalizzazione delle stringhe `audioLanguages` (es. `ita/eng` == `eng/ita`)
- [x] Flag `--ignore-unknown` per escludere `und` dal calcolo dei mismatch
- [x] Flag `--timeout` per impostare il timeout di lettura HTTP
- [ ] Supporto per esportazione CSV / Excel
- [ ] Aggiunta logging su file (es. `log/scan.log`)
- [ ] Opzione `--filter` per visualizzare solo stagioni miste
- [ ] Output con colori / evidenziazione CLI
- [ ] Flag per includere solo serie complete
- [ ] Ordinamento output per gravità / numero di mismatch
 - [x] Report copertura lingue desiderate (`--wanted-langs`)
 - [x] Alias `--wanted-lang`
 - [x] Ignora serie Anime (`--ignore-anime`)

---

## 🤖 Automazione

- [ ] Supporto cronjob (`--silent` o `--notify`)
- [ ] Dockerfile con `uv` preconfigurato
- [ ] Notifica Telegram / Email per mismatch rilevati

---

## 🌐 Interfaccia

- [ ] CLI interattiva (es. con `InquirerPy` o `rich.prompt`)
- [ ] Web UI minimale con Streamlit o Flask
- [ ] Modalità "audit" solo con statistiche

---

## 🧹 Pulizia

- [ ] Controllo episodi senza file associati
- [ ] Rilevamento serie duplicate / alias
- [ ] Supporto per merge multi-lingua coerente

---

## 💡 Idee extra

- [ ] Integrazione con Radarr per film
- [ ] Report HTML generabile offline
- [ ] Supporto multi-profilo Sonarr da config YAML
