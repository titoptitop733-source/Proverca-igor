# Semestrálny projekt - Programovanie v Pythone

**Študent:** Ivan Nerodyk
**Názov projektu:** DROPZONE – sledovanie cien PC hier

Podrobné a aktuálne znenie zadania je na stránke predmetu:
https://marek-horvath.github.io/python/projekt/

## Zadanie

Navrhnite a implementujte vlastný individuálny projekt v jazyku Python. Téma je voľná, projekt však musí riešiť konkrétny problém alebo poskytovať ucelenú funkcionalitu.

Projekt musí zmysluplne kombinovať minimálne 3 technologické oblasti, napríklad:

- skriptovanie, súbory alebo automatizácia;
- GUI alebo webové používateľské rozhranie;
- HTTP a externé API;
- databáza;
- spracovanie alebo vizualizácia dát;
- web scraping alebo automatizácia prehliadača;
- web backend;
- iná primeraná Python technológia.

Samotný import knižnice sa nepočíta. Každá zvolená technológia musí riešiť reálnu časť projektu.

## Míľniky a hodnotenie

| Časť | Termín | Body |
|------|--------|------|
| MVP - prvá funkčná verzia | 6. týždeň semestra | 30 |
| Finálna aplikácia | 11.-13. týždeň semestra | 40 |
| Technická dokumentácia PDF | finálne odovzdanie | 20 |
| Približne 5-minútové video | finálne odovzdanie | 10 |
| **Spolu** | | **100** |

MVP musí obsahovať reálny spustiteľný kód a základ hlavnej funkcionality. Nestačí prázdna štruktúra, mockup ani dokument s návrhom.

## Požadovaný obsah repozitára

- zdrojový kód rozdelený do zmysluplných modulov;
- tento README.md doplnený o informácie o projekte;
- pyproject.toml alebo requirements.txt;
- .gitignore;
- .env.example, ak projekt používa konfiguračné premenné;
- testy primerané typu projektu;
- potrebné assets alebo malé datasety;
- finálna technická dokumentácia v PDF, odporúčane v rozsahu približne 10-15 strán.

Video necommitujte ako veľký binárny súbor do Git repozitára. Spôsob jeho odovzdania bude oznámený samostatne.

## Pravidlá práce

- Commitujte priebežne. Jeden veľký commit na konci sa nepovažuje za priebežnú prácu.
- Projekt musí byť možné spustiť na inom počítači podľa návodu v README.
- Necommitujte heslá, API kľúče, tokeny, osobné dáta ani obsah súboru .env.
- Nepoužívajte hardcoded absolútne cesty závislé od vášho počítača.
- Ošetrite neplatné vstupy a bežné chybové situácie.
- Uprednostnite menší funkčný a kvalitný projekt pred veľkým nefunkčným riešením.

## Použitie AI

AI nástroje sú povolené. Za celý odovzdaný projekt však zodpovedáte vy. Musíte rozumieť použitému kódu, vedieť ho vysvetliť, upraviť a obhájiť svoje technické rozhodnutia.

Výraznejšie použitie AI, externých šablón, tutoriálov alebo prevzatého kódu uveďte v dokumentácii. Nepochopenie podstatnej časti riešenia môže viesť k bodovej penalizácii alebo k nesplneniu podmienok predmetu.

## Výskumné spracovanie

Odovzdaný projekt môže byť použitý na pedagogický alebo vedecký výskum. Pred spracovaním budú odstránené priame identifikátory študenta a výsledky budú prezentované iba v anonymizovanej alebo súhrnnej podobe.

---

# O projekte

## Krátky popis

DROPZONE je aplikácia na sledovanie cien PC hier v obchodoch ako Steam, GOG, Humble Store alebo Epic Games Store. Zaznamenáva ceny z API CheapShark do databázy SQLite, zobrazuje ich vývoj a porovnanie obchodov a na základe histórie odporúča, či hru kúpiť teraz, alebo počkať. Je určená hráčom, ktorí chcú kupovať hry výhodne. Hlavným cieľom je ušetriť čas pri sledovaní zliav a pomôcť s rozhodnutím o kúpe pomocou vysvetliteľného odporúčania.

### Čo projekt rieši

Ceny hier sa často menia a v jednotlivých obchodoch sa líšia. Ručné porovnávanie vo viacerých obchodoch je zdĺhavé, ľahko sa premešká zľava, alebo sa hra kúpi tesne pred väčším výpredajom. DROPZONE zaznamenáva ceny sledovaných hier zo všetkých obchodov, ukazuje históriu a historické minimum a pri každej hre uvedie, či je cena výhodná, vrátane dôvodov odporúčania. Používateľ si môže nastaviť cieľovú cenu a aplikácia ho upozorní, keď ju cena dosiahne.

## Aktuálna funkcionalita

- vyhľadanie ľubovoľnej PC hry (CheapShark API) a pridanie do zoznamu sledovaných hier (wishlist) s voliteľnou cieľovou cenou;
- záznam cien zo všetkých obchodov do SQLite (tzv. snímky) s minimálnym intervalom medzi kontrolami;
- štatistiky cez pandas: historické minimum, priemer, maximum, frekvencia zliav;
- odporúčanie **BUY NOW / GOOD DEAL / WAIT** s vysvetlením dôvodov;
- cieľové ceny so stavom (dosiahnutá, takmer, čaká sa) a upozornenia;
- prehľad (dashboard) s potenciálnou úsporou, poklesmi cien a históriou udalostí;
- stránka **Discover** s aktuálnymi zľavami, filtrami (obchod, cena, zľava) a triedením;
- zobrazenie cien v USD, EUR alebo GBP (kurzy ECB z Frankfurter API), tmavá a svetlá téma;
- tri rozhrania nad spoločnou logikou: **webová aplikácia** (FastAPI), desktopová aplikácia (Tkinter) a príkazový riadok;
- zber cien v cloude (GitHub Actions, každých 6 hodín) a jeho zlúčenie s lokálnou databázou;
- 107 automatických testov, kontrola štýlu (ruff) a typov (mypy), CI v GitHub Actions.

## Plánovaná funkcionalita

Jadro je hotové a funkčné. Do finálnej verzie zostáva:

| Krok | Čo | Prečo |
|------|----|-------|
| 1 | **Dlhšia história cien** – zber v cloude beží každých 6 hodín a história rastie sama | odporúčanie a grafy majú zmysel až s dátami za týždne |
| 2 | **Doladenie odporúčania** na reálnych dátach (prahy v `analysis.py`) a testy pre nové prípady | súčasné prahy sú odôvodnený prvý odhad |
| 3 | Možné rozšírenia: e-mailové alebo systémové upozornenie pri dosiahnutí cieľa, porovnanie viacerých hier v jednom grafe, export do CSV | väčší úžitok; každé je voliteľné a malé |
| 4 | Technická dokumentácia (PDF, 10–15 strán) a približne 5-minútové video | povinné výstupy finálneho odovzdania |
| 5 | Záverná kontrola: viac testov okrajových prípadov, úprava README, overenie behu na čistom klone | reprodukovateľnosť |

## Použité technologické oblasti

- **HTTP a externé API:** klienty `httpx` pre CheapShark (ceny, zľavy, obchody) a Frankfurter (kurzy mien); timeouty, mapovanie chýb na vlastnú výnimku, validácia odpovedí a cache kurzov.
- **Databáza:** SQLite s tabuľkami hier, obchodov a histórie cien; parametrizované dotazy, window funkcia na výber najlepšej ceny snímky, automatické migrácie.
- **Spracovanie a vizualizácia dát:** pandas počíta štatistiky a odporúčanie, matplotlib kreslí grafy (PNG aj vo vnútri Tkinter okna).
- **Web backend:** FastAPI REST API s Pydantic modelmi požiadaviek a odpovedí a automatickou dokumentáciou na `/docs`.
- **Používateľské rozhranie:** webové rozhranie (HTML, CSS, JavaScript bez build kroku) a desktopová aplikácia v Tkinteri.
- **Skriptovanie a automatizácia:** CLI (`argparse`), konfigurácia cez `.env`, `pathlib`, `subprocess` (git) a plánovaný workflow GitHub Actions na zber cien.

## Inštalácia a spustenie

Požiadavky: Python 3.10 alebo novší a internetové pripojenie (API kľúče nie sú potrebné). Stiahnite repozitár (`git clone`), prejdite do jeho priečinka a v termináli spustite:

```bash
python -m venv .venv
# Windows:     .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # všetky testy prejdú, nepotrebujú internet
game-tracker web            # otvorí webové rozhranie na http://127.0.0.1:8000
```

Databáza `data/game_tracker.db` sa vytvorí automaticky pri prvom spustení. Konfigurácia je voliteľná: súbor `.env.example` skopírujte na `.env` (všetky hodnoty majú predvolené nastavenie).

| Premenná | Predvolená hodnota | Význam |
|----------|--------------------|--------|
| `GT_API_BASE_URL` | `https://www.cheapshark.com/api/1.0` | API s cenami |
| `GT_FX_API_URL` | `https://api.frankfurter.dev/v1` | API s kurzami mien |
| `GT_DB_PATH` | `data/game_tracker.db` | súbor databázy |
| `GT_HTTP_TIMEOUT` | `10` | timeout HTTP v sekundách |
| `GT_MIN_SNAPSHOT_INTERVAL_HOURS` | `6` | minimálny odstup dvoch kontrol ceny hry |
| `GT_WEB_HOST`, `GT_WEB_PORT` | `127.0.0.1`, `8000` | adresa webového servera (len lokálne) |
| `GT_SYNC_REPO` | prázdne | voliteľné: repozitár so zberom cien v cloude |

Ďalšie spôsoby spustenia: `game-tracker gui` (desktopová aplikácia), `game-tracker --help` (zoznam príkazov).

## Základné použitie

Hlavný scenár vo webovom rozhraní: kliknite na **Track a game**, vyhľadajte hru a pridajte ju. Aplikácia uloží prvú snímku cien zo všetkých obchodov. V detaile hry uvidíte graf ceny, porovnanie obchodov a kartu **Buy or wait?** s odporúčaním a dôvodmi. Nastavte cieľovú cenu – keď ju kontrola cien dosiahne, aplikácia upozorní. Na stránke **Discover** nájdete aktuálne zľavy.

Ten istý scenár v príkazovom riadku:

```bash
game-tracker search "hollow knight"       # nájde hru a jej ID
game-tracker add 165363 --target 10       # sledovanie s cieľovou cenou (USD)
game-tracker list                         # wishlist s cenami a odporúčaním
game-tracker update                       # kontrola cien (--force ignoruje interval)
game-tracker stats 165363                 # štatistiky a odporúčanie
```

## Ďalšie informácie

### Štruktúra projektu

```
src/game_tracker/
├── api_client.py    # klient CheapShark API
├── currency.py      # kurzy mien (Frankfurter, cache)
├── models.py        # dátové triedy
├── storage.py       # SQLite repozitár a migrácie
├── collector.py     # pridanie hry, aktualizácia cien, upozornenia
├── analysis.py      # pandas štatistiky a odporúčanie
├── insights.py      # stav cieľa, udalosti, súhrn dashboardu
├── overview.py, service.py   # spoločná logika pre všetky rozhrania
├── sync.py          # zber v cloude: wishlist.json, zlúčenie databáz
├── charts.py, config.py, cli.py
├── ui/              # desktopová aplikácia (Tkinter)
└── web/             # FastAPI (app, schemas, serializers) a frontend (static/)
tests/               # pytest testy
docs/                # technická dokumentácia (PDF) a jej generátor
.github/workflows/   # tests.yml (CI) a collect-prices.yml (zber cien)
```

### Ako funguje odporúčanie

Odporúčanie vychádza z najlepšej ceny každej snímky a z historického minima, ktoré hlási CheapShark:

1. **BUY NOW** – cena dosiahla cieľ alebo je najviac o 10 % nad historickým minimom;
2. **GOOD DEAL** – zľava aspoň 50 % alebo cena aspoň o 15 % pod priemerom;
3. **WAIT** – hra už bola aspoň o 30 % lacnejšia alebo momentálne nie je v zľave.

Pri menej ako troch snímkach sa uvedie nízka spoľahlivosť. Pravidlá vysvetľujú minulé ceny, nepredpovedajú budúce výpredaje. Prahy sú konštanty na začiatku `analysis.py`.

### Zber cien v cloude (GitHub Actions)

Workflow `.github/workflows/collect-prices.yml` kontroluje ceny každých 6 hodín aj bez zapnutého počítača a ukladá databázu do vetvy `data`. Zoznam hier berie zo súboru `data/wishlist.json` (`game-tracker sync --push`). Príkaz `game-tracker sync` (a štart webu) nové snímky zlúči s lokálnou databázou – nič lokálne sa neprepíše. Funkcia je voliteľná a vyžaduje nastavenie `GT_SYNC_REPO`; bez nej aplikácia beží normálne.

### Testy a kvalita kódu

```bash
pytest                      # 107 testov, bez prístupu na internet (mock HTTP, dočasná databáza)
ruff check src tests        # štýl kódu
mypy src/game_tracker       # kontrola typov
```

### Bezpečnosť

Webový server počúva iba na `127.0.0.1`; všetky SQL dotazy sú parametrizované; vstupy API validuje Pydantic; text z externých API sa vo frontende escapuje; žiadne tajomstvá nie sú v kóde (konfigurácia je v `.env`, ktorý je v `.gitignore`).

## Zdroje a použité nástroje

- CheapShark API (ceny hier): https://apidocs.cheapshark.com
- Frankfurter API (referenčné kurzy ECB): https://frankfurter.dev
- Knižnice: httpx, pandas, matplotlib, FastAPI, Pydantic, uvicorn, python-dotenv, pytest, ruff, mypy; ikony Lucide (licencia ISC); obrázky hier zo Steam CDN.
- Dokumentácia jazyka Python a použitých knižníc; materiály predmetu: https://marek-horvath.github.io/python/
- **AI nástroje:** pri projekte som používal AI asistenta Claude (Anthropic) na návrh témy a architektúry, generovanie častí kódu, testov a dokumentácie a na hľadanie chýb. Kód som spúšťal, testoval na reálnych dátach (pytest, ruff, mypy), prechádzal a upravoval; podrobnosti sú v technickej dokumentácii (`docs/documentation.pdf`).