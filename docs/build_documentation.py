"""Generate docs/documentation.pdf (technical documentation of the project).

Usage (from the project root, with the virtual environment activated):

    pip install -e ".[docs]"
    python docs/build_documentation.py

The author and repository are set in the defaults at the top of the file. Optional:
--author NAME, --year "2026/2027" and --repo URL. To refresh the screenshots from your own
running application first, see docs/take_screenshots.py. The text is in Slovak (the
language of the course).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

# ---------------------------------------------------------------------- defaults
# Normally set on the command line (--author, --year, --repo), not here.
AUTHOR = "Ivan Nerodyk"
ACADEMIC_YEAR = "2026/2027"
PROJECT_TITLE = "DROPZONE – sledovanie cien PC hier"
REPOSITORY = "https://git.kpi.fei.tuke.sk/python/2026/ivan-nerodyk"
GITHUB_MIRROR = "https://github.com/titoptitop733-source/Proverca-igor"
# ----------------------------------------------------------------------------------

DOCS = Path(__file__).resolve().parent
IMG = DOCS / "img"
OUTPUT = DOCS / "documentation.pdf"

ACCENT = colors.HexColor("#3d7a00")
DARK = colors.HexColor("#16191f")
GREY = colors.HexColor("#5b6370")
LIGHT = colors.HexColor("#eef1f4")
LINE = colors.HexColor("#c9ced6")


# ---------------------------------------------------------------------- fonts

def register_fonts() -> tuple[str, str, str]:
    """Register the DejaVu fonts that ship with matplotlib (they contain Slovak diacritics).

    Using the bundled files means no operating-system font paths are needed.
    """
    fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, filename in (
        ("Body", "DejaVuSans.ttf"),
        ("Body-Bold", "DejaVuSans-Bold.ttf"),
        ("Body-Italic", "DejaVuSans-Oblique.ttf"),
        ("Body-BoldItalic", "DejaVuSans-BoldOblique.ttf"),
        ("Mono", "DejaVuSansMono.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                  italic="Body-Italic", boldItalic="Body-BoldItalic")
    return "Body", "Body-Bold", "Mono"


BODY, BOLD, MONO = register_fonts()

STYLES = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=24, leading=30, alignment=TA_CENTER,
                            textColor=DARK, spaceAfter=10),
    "subtitle": ParagraphStyle("subtitle", fontName=BODY, fontSize=13, leading=18,
                               alignment=TA_CENTER, textColor=GREY),
    "center": ParagraphStyle("center", fontName=BODY, fontSize=12, leading=18, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=17, leading=22, textColor=DARK,
                         spaceBefore=6, spaceAfter=10, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=12.5, leading=17, textColor=ACCENT,
                         spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "body": ParagraphStyle("body", fontName=BODY, fontSize=10.3, leading=15, alignment=TA_JUSTIFY,
                           spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName=BODY, fontSize=10.3, leading=14.5, leftIndent=14,
                             bulletIndent=4, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=8.8, leading=11.5),
    "cellb": ParagraphStyle("cellb", fontName=BOLD, fontSize=8.8, leading=11.5),
    "caption": ParagraphStyle("caption", fontName=BODY, fontSize=8.8, leading=12, textColor=GREY,
                              alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=8.2, leading=10.8, backColor=LIGHT,
                           borderPadding=6, leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=10),
    "toc1": ParagraphStyle("toc1", fontName=BOLD, fontSize=9.6, leading=12.5, spaceBefore=0,
                           spaceAfter=0),
    "toc2": ParagraphStyle("toc2", fontName=BODY, fontSize=8.6, leading=10.8, leftIndent=16,
                           spaceBefore=0, spaceAfter=0, textColor=GREY),
}

FIG = {"n": 0}
TAB = {"n": 0}


# ---------------------------------------------------------------------- building blocks

class DocTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable: object) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            level = 0 if flowable.style.name == "h1" else 1
            self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))


def h1(text: str) -> Paragraph:
    return Paragraph(text, STYLES["h1"])


def h2(text: str) -> Paragraph:
    return Paragraph(text, STYLES["h2"])


def p(text: str) -> Paragraph:
    return Paragraph(text, STYLES["body"])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(item, STYLES["bullet"], bulletText="•") for item in items]


def numbered(items: list[str]) -> list[Paragraph]:
    return [Paragraph(item, STYLES["bullet"], bulletText=f"{i}.") for i, item in enumerate(items, 1)]


def code(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), STYLES["code"])


def table(rows: list[list[str]], widths: list[float], caption: str | None = None,
          keep: bool = True):
    """Table with a numbered caption.

    Short tables are kept on one page; pass keep=False for long ones, which may then
    continue on the next page (the header row is repeated).
    """
    data = [[Paragraph(cell, STYLES["cellb" if r == 0 else "cell"]) for cell in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    parts: list = [t]
    if caption:
        TAB["n"] += 1
        parts.append(Paragraph(f"Tabuľka {TAB['n']}: {caption}", STYLES["caption"]))
    return KeepTogether(parts) if keep else parts


def flatten(items):
    """Section functions may contain nested lists (tables that are allowed to split)."""
    for item in items:
        if isinstance(item, (list, tuple)):
            yield from flatten(item)
        else:
            yield item


def figure(name: str, caption: str, width_cm: float = 16.0) -> KeepTogether:
    path = IMG / name
    if not path.is_file():
        return KeepTogether([p(f"<i>[Chýba obrázok {name}]</i>")])
    from reportlab.lib.utils import ImageReader

    iw, ih = ImageReader(str(path)).getSize()
    width = width_cm * cm
    FIG["n"] += 1
    return KeepTogether([
        Image(str(path), width=width, height=width * ih / iw),
        Paragraph(f"Obrázok {FIG['n']}: {caption}", STYLES["caption"]),
    ])


def on_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(BODY, 8.5)
    canvas.setFillColor(GREY)
    canvas.drawString(2.2 * cm, 1.3 * cm, PROJECT_TITLE)
    canvas.drawRightString(A4[0] - 2.2 * cm, 1.3 * cm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(2.2 * cm, 1.7 * cm, A4[0] - 2.2 * cm, 1.7 * cm)
    canvas.restoreState()


# ---------------------------------------------------------------------- diagram

def build_architecture_diagram(path: Path) -> None:
    """Layered architecture: interfaces -> application layer -> domain -> data/integrations."""
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 66)
    ax.axis("off")

    def box(x, y, w, title, sub, face, h=7.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35,rounding_size=1.1",
                                    linewidth=1.1, edgecolor="#2a2f38", facecolor=face))
        ax.text(x + w / 2, y + h / 2 + 1.3, title, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color="#16191f")
        ax.text(x + w / 2, y + h / 2 - 1.8, sub, ha="center", va="center", fontsize=7.6,
                color="#3c434d")

    def arrow(x1, y1, x2, y2, label=""):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color="#5b6370", shrinkA=2, shrinkB=2))
        if label:
            ax.text(x1 + 1.2, (y1 + y2) / 2, label, fontsize=7.5, color="#5b6370", va="center")

    for y, label in ((60.5, "Rozhrania"), (34.5, "Aplikačná vrstva"),
                     (22.5, "Doménová logika"), (9.5, "Dáta a integrácie")):
        ax.text(0, y, label, fontsize=8.5, color="#5b6370", rotation=90, va="center", ha="left")

    ui, app, dom, data = "#e8f5d6", "#e6ebff", "#f1f2f4", "#fff2df"
    box(8, 55, 26, "Webový frontend", "HTML/CSS/JS v prehliadači", ui)
    box(40, 55, 26, "Desktop GUI", "Tkinter (ui/)", ui)
    box(72, 55, 26, "CLI", "argparse (cli.py)", ui)
    box(8, 42.5, 26, "REST API", "FastAPI + Pydantic (web/)", ui)
    box(8, 30, 90, "service.py  ·  overview.py  ·  insights.py",
        "spoločná logika pre všetky tri rozhrania", app)
    box(8, 17.5, 26, "collector.py", "pridanie hry, aktualizácia cien", dom)
    box(40, 17.5, 22, "analysis · charts", "pandas, matplotlib", dom)
    box(8, 4, 20, "storage.py", "SQLite databáza", data)
    box(31, 4, 20, "api_client.py", "CheapShark API (ceny)", data)
    box(54, 4, 20, "currency.py", "Frankfurter API (ECB)", data)
    box(77, 4, 21, "sync.py", "GitHub Actions (cloud)", data)

    arrow(21, 55, 21, 50.3, "HTTP / JSON")
    arrow(21, 42.5, 21, 38.2)
    arrow(53, 55, 53, 38.2)
    arrow(85, 55, 85, 38.2)
    arrow(21, 30, 21, 25.3)
    arrow(51, 30, 51, 25.3)
    arrow(64, 30, 64, 11.8)
    arrow(87, 30, 87, 11.8)
    arrow(18, 17.5, 18, 11.8)
    arrow(30, 17.5, 40, 11.8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------- content

def title_page() -> list:
    return [
        Spacer(1, 2.2 * cm),
        Paragraph("Technická univerzita v Košiciach", STYLES["center"]),
        Paragraph("Fakulta elektrotechniky a informatiky", STYLES["center"]),
        Spacer(1, 4.2 * cm),
        Paragraph("Programovanie v Pythone", STYLES["subtitle"]),
        Paragraph("Semestrálny projekt – technická dokumentácia", STYLES["subtitle"]),
        Spacer(1, 0.9 * cm),
        Paragraph(PROJECT_TITLE, STYLES["title"]),
        Spacer(1, 6.5 * cm),
        Paragraph(f"Autor: <b>{AUTHOR}</b>", STYLES["center"]),
        Paragraph(f"Akademický rok: {ACADEMIC_YEAR}", STYLES["center"]),
        Paragraph(f"Repozitár: {REPOSITORY}", STYLES["center"]),
        Paragraph(f"GitHub (pracovná kópia a zber cien): {GITHUB_MIRROR}", STYLES["center"]),
        NextPageTemplate("content"),
        PageBreak(),
    ]


def contents() -> list:
    toc = TableOfContents()
    toc.levelStyles = [STYLES["toc1"], STYLES["toc2"]]
    toc.dotsMinLevel = 0
    return [Paragraph("Obsah", STYLES["h1"].clone("toc_title")), toc, PageBreak()]


def section_intro() -> list:
    return [
        h1("1 Úvod"),
        p("Ceny digitálnych hier sa často menia a v jednotlivých obchodoch (Steam, GOG, Humble "
          "Store, Epic Games Store a ďalšie) sa líšia. Kto chce hru kúpiť výhodne, musí ceny "
          "sledovať ručne vo viacerých obchodoch. Ľahko tak premešká zľavu, alebo naopak kúpi hru "
          "tesne pred väčším výpredajom."),
        p("Projekt <b>DROPZONE</b> tento problém rieši. Aplikácia pravidelne zaznamenáva ceny "
          "sledovaných hier zo všetkých obchodov do lokálnej databázy, zobrazuje vývoj ceny, "
          "porovnáva obchody a na základe zaznamenanej histórie odporúča, či je aktuálna cena "
          "výhodná (<i>kúpiť teraz</i>), alebo sa oplatí počkať. Používateľ si môže nastaviť "
          "cieľovú cenu a aplikácia ho upozorní, keď ju cena dosiahne."),
        p("Tému som si zvolil, pretože hry na PC kupujem pravidelne a porovnávanie cien je pre mňa "
          "reálny problém. Téma zároveň prirodzene spája viacero oblastí predmetu: prácu s "
          "externými API, databázu, analýzu dát, webový backend a používateľské rozhranie. Každá "
          "z týchto oblastí rieši skutočnú časť problému, nie je pridaná len formálne."),
        p("Hlavným cieľom bolo vytvoriť aplikáciu, ktorá pracuje s <b>reálnymi dátami</b> "
          "(nie s ukážkovými), dá sa spustiť na inom počítači iba podľa README, bez API kľúčov, "
          "a ktorej odporúčania sú vysvetliteľné a overiteľné – aplikácia vždy uvádza dôvody, "
          "prečo odporúča kúpiť alebo počkať. Ceny sa zbierajú automaticky aj v cloude "
          "(GitHub Actions), takže história vzniká aj vtedy, keď je počítač vypnutý."),
    ]


def section_requirements() -> list:
    return [
        h1("2 Požiadavky a funkcionalita"),
        h2("2.1 Funkčné požiadavky"),
        *bullets([
            "vyhľadanie ľubovoľnej PC hry podľa názvu a jej pridanie do zoznamu sledovaných hier (wishlist),",
            "pravidelný záznam cien zo všetkých obchodov (tzv. snímky) do databázy,",
            "história ceny, štatistiky (historické minimum, priemer, maximum, frekvencia zliav) a graf,",
            "odporúčanie <i>BUY NOW / GOOD DEAL / WAIT</i> s vysvetlením dôvodov,",
            "cieľová cena so stavom <i>dosiahnutá / takmer / čaká sa</i> a upozornenie pri jej dosiahnutí,",
            "prehľad (dashboard) s potenciálnou úsporou, poklesmi cien a históriou udalostí,",
            "stránka <i>Discover</i> s aktuálnymi zľavami, filtrami (obchod, cena, zľava) a triedením,",
            "zobrazenie cien v USD, EUR alebo GBP podľa aktuálnych kurzov ECB,",
            "automatický zber cien v cloude každých 6 hodín (GitHub Actions) a jeho zlúčenie s lokálnou databázou,",
            "tmavá a svetlá téma (alebo podľa systému),",
            "tri rozhrania nad spoločnou logikou: webová aplikácia, desktopová aplikácia a CLI.",
        ]),
        h2("2.2 Nefunkčné požiadavky"),
        *bullets([
            "spustiteľnosť podľa README bez API kľúčov a bez ručne vytvorenej databázy,",
            "odolnosť voči výpadku externých služieb – aplikácia nespadne, zobrazí zrozumiteľnú chybu,",
            "server dostupný iba z lokálneho počítača (127.0.0.1),",
            "automatické testy bez prístupu na internet,",
            "konfigurácia oddelená od kódu (súbor <font name='%s'>.env</font>)." % MONO,
        ]),
        h2("2.3 Používateľské scenáre"),
        table([
            ["Scenár", "Priebeh"],
            ["S1 Sledovanie novej hry", "Používateľ klikne na <i>Track a game</i>, vyhľadá hru a pridá ju. "
             "Aplikácia uloží prvú snímku cien a hru zobrazí v prehľade."],
            ["S2 Rozhodnutie o kúpe", "Otvorí detail hry, pozrie graf, porovnanie obchodov a kartu "
             "<i>Buy or wait?</i> s dôvodmi odporúčania."],
            ["S3 Hľadanie zľavy", "Na stránke Discover nastaví maximálnu cenu a minimálnu zľavu, "
             "výhodnú hru začne sledovať jedným kliknutím."],
            ["S4 Čakanie na cenu", "Nastaví cieľovú cenu. Pri ďalšej kontrole cien, keď cena klesne "
             "pod cieľ, aplikácia zobrazí upozornenie."],
        ], [4.2, 12.3], "Hlavné používateľské scenáre"),
        h2("2.4 MVP a finálna verzia"),
        table([
            ["Oblasť", "MVP (6. týždeň)", "Finálna verzia"],
            ["Rozhranie", "CLI", "webová aplikácia, desktop GUI, CLI"],
            ["Dáta", "wishlist, snímky cien", "+ obrázky hier, ponuky obchodov, kurzy mien"],
            ["Analýza", "–", "štatistiky (pandas), odporúčanie, grafy, dashboard"],
            ["Externé API", "CheapShark (vyhľadávanie, ceny)", "+ CheapShark deals, Frankfurter (kurzy)"],
            ["Automatizácia", "ručné spustenie príkazu", "GitHub Actions každých 6 h, synchronizácia"],
            ["Kvalita", "20 testov", "120 testov, ruff, mypy"],
        ], [3.2, 5.6, 7.7], "Porovnanie MVP a finálnej verzie"),
    ]


def section_design() -> list:
    return [
        h1("3 Návrh riešenia"),
        p("Aplikácia je rozdelená do vrstiev. Rozhrania (web, desktop, CLI) neobsahujú aplikačnú "
          "logiku – iba zobrazujú dáta a volajú spoločnú aplikačnú vrstvu. Vďaka tomu sa rovnaký "
          "výpočet odporúčania alebo štatistík používa vo všetkých troch rozhraniach a dá sa "
          "testovať bez grafického rozhrania. Celkové usporiadanie ukazuje obrázok 1."),
        h2("3.1 Princípy návrhu"),
        *bullets([
            "<b>Oddelenie rozhrania od logiky</b> – moduly <i>analysis</i>, <i>collector</i> a <i>insights</i> "
            "nepoznajú Tkinter ani FastAPI.",
            "<b>Vkladanie závislostí</b> – <font name='%s'>create_app(service, rates)</font> dostane služby ako "
            "parametre, takže testy môžu použiť falošný zdroj dát bez siete." % MONO,
            "<b>Rozhranie zdroja dát</b> – trieda <font name='%s'>GameDataSource</font> (typing.Protocol) "
            "opisuje, čo musí zdroj vedieť. Skutočný klient aj testovací fake ju spĺňajú." % MONO,
            "<b>Krátke databázové spojenia</b> – každá operácia v <i>service.py</i> otvorí vlastné spojenie, "
            "pretože spojenie sqlite3 sa nesmie zdieľať medzi vláknami (web server a GUI používajú vlákna).",
        ]),
        figure("architecture.png", "Architektúra aplikácie (šípky ukazujú smer volaní)", 14.0),
        h2("3.2 Tok dát pri aktualizácii cien"),
        *numbered([
            "Rozhranie zavolá <font name='%s'>TrackerService.update_prices()</font>." % MONO,
            "Pre každú sledovanú hru sa overí, či od poslednej snímky uplynul nastavený interval (6 h).",
            "Klient CheapShark stiahne aktuálne ponuky všetkých obchodov a historické minimum.",
            "Ponuky sa uložia ako jedna snímka do tabuľky <i>price_history</i>.",
            "Ak najlepšia cena dosiahla cieľovú cenu, vznikne upozornenie (PriceAlert).",
            "Chyba pri jednej hre nezastaví aktualizáciu ostatných – zapíše sa do výsledného reportu.",
        ]),
        h2("3.3 Zber cien v cloude"),
        p("Ceny sa zaznamenávajú len vtedy, keď aplikácia beží. Aby história vznikala aj bez zapnutého "
          "počítača, kontroluje ceny aj plánovaný workflow GitHub Actions. Každý údaj má práve jedného "
          "vlastníka, preto medzi počítačom a cloudom nevznikajú konflikty:"),
        table([
            ["Krok", "Kde", "Čo sa deje"],
            ["1", "počítač", "<font name='%s'>game-tracker sync --push</font> zapíše sledované hry a cieľové ceny "
             "do <i>data/wishlist.json</i> a odošle súbor do repozitára" % MONO],
            ["2", "GitHub Actions", "každých 6 h: <font name='%s'>game-tracker collect</font> prečíta wishlist.json, "
             "obnoví databázu z vetvy <i>data</i> a skontroluje ceny" % MONO],
            ["3", "GitHub", "databáza sa uloží ako jediný commit vo vetve <i>data</i>, repozitár preto nerastie"],
            ["4", "počítač", "<font name='%s'>game-tracker web</font> pri štarte stiahne databázu a zlúči chýbajúce snímky" % MONO],
        ], [1.2, 3.3, 12.0], "Tok dát medzi počítačom a cloudom"),
    ]


def section_technologies() -> list:
    return [
        h1("4 Použité technológie"),
        p("Projekt kombinuje šesť technologických oblastí predmetu (ďalej testovanie a kontrolu kvality). Každá rieši konkrétnu časť "
          "problému, ako ukazuje nasledujúca tabuľka."),
        table([
            ["Oblasť", "Knižnica", "Účel v projekte", "Prečo"],
            ["HTTP a externé API", "httpx", "klient pre CheapShark a Frankfurter",
             "timeouty, jednoduché mapovanie chýb, MockTransport na testy bez siete"],
            ["Databázy", "sqlite3", "wishlist, obchody, história cien",
             "súčasť štandardnej knižnice, netreba server; podpora window funkcií"],
            ["Data Science", "pandas, matplotlib", "štatistiky, odporúčanie, grafy",
             "rýchla práca s časovými radmi; grafy pre CLI aj Tkinter"],
            ["Web backend", "FastAPI, Pydantic, uvicorn", "REST API pre webové rozhranie",
             "validácia vstupov, automatická dokumentácia OpenAPI (/docs)"],
            ["Používateľské rozhranie", "HTML/CSS/JS, Tkinter", "webová a desktopová aplikácia",
             "web bez build kroku (netreba Node.js); Tkinter je súčasť Pythonu"],
            ["Skriptovanie a automatizácia", "argparse, pathlib, subprocess, GitHub Actions",
             "CLI, konfigurácia, git push wishlistu, plánovaný zber cien",
             "konfigurácia mimo kódu; zber cien bez zapnutého počítača"],
            ["Kvalita kódu", "pytest, ruff, mypy", "120 testov, štýl, kontrola typov",
             "fixtures, tmp_path, monkeypatch; type hints overené nástrojom"],
        ], [3.0, 3.4, 4.5, 5.6], "Technologické oblasti a ich použitie", keep=False),
        p("Závislosti sú uvedené v súbore <font name='%s'>pyproject.toml</font> a inštalujú sa jedným "
          "príkazom <font name='%s'>pip install -e \".[dev]\"</font>." % (MONO, MONO)),
    ]


def section_implementation() -> list:
    return [
        h1("5 Implementácia"),
        h2("5.1 Moduly"),
        table([
            ["Modul", "Zodpovednosť"],
            ["api_client.py", "HTTP klient CheapShark: vyhľadávanie, detail hry, zľavy, obchody; prevod JSON na dátové triedy"],
            ["currency.py", "kurzy mien z Frankfurter API, vyrovnávacia pamäť na 12 h, záložné správanie"],
            ["models.py", "nemenné dátové triedy (dataclass): Game, Deal, PricePoint, DealListing, …"],
            ["storage.py", "repozitár nad SQLite, parametrizované dotazy, automatické migrácie"],
            ["collector.py", "pridanie hry, aktualizácia cien, interval snímok, upozornenia"],
            ["analysis.py", "štatistiky cez pandas a pravidlá odporúčania"],
            ["insights.py", "stav cieľovej ceny, udalosti (pokles, nové minimum), súhrn dashboardu"],
            ["overview.py, service.py", "spojenie dát a analýzy; fasáda pre GUI a web, bezpečná pre vlákna"],
            ["sync.py", "zber v cloude: wishlist.json, stiahnutie a zlúčenie databázy, git push"],
            ["web/app.py, schemas.py", "FastAPI aplikácia, endpointy, Pydantic modely požiadaviek a odpovedí"],
            ["web/static/", "frontend: index.html, css/app.css, js/ (ES moduly, vlastné SVG grafy)"],
            ["ui/", "Tkinter aplikácia, beh HTTP požiadaviek mimo hlavného vlákna"],
            ["cli.py, config.py", "príkazový riadok, načítanie a validácia konfigurácie"],
        ], [4.2, 12.3], "Hlavné moduly (src/game_tracker)", keep=False),
        h2("5.2 Dátový model"),
        p("Databáza má tri tabuľky. Každé spustenie aktualizácie vytvorí pre hru jednu <i>snímku</i> – "
          "skupinu riadkov v <i>price_history</i> s rovnakým časom <i>recorded_at</i>, jeden riadok pre každý obchod."),
        table([
            ["Tabuľka", "Stĺpce", "Poznámka"],
            ["games", "game_id (PK), title, target_price, added_at, cheapest_ever_price, steam_app_id, thumb_url",
             "CHECK: target_price ≥ 0"],
            ["stores", "store_id (PK), name, is_active", "zoznam obchodov z API"],
            ["price_history", "id (PK), game_id (FK, ON DELETE CASCADE), store_id, price, retail_price, "
             "savings_percent, recorded_at", "index (game_id, recorded_at)"],
        ], [3.0, 9.0, 4.5], "Databázová schéma"),
        p("Nové stĺpce pridané počas vývoja (napr. <i>steam_app_id</i>) sa do existujúcej databázy doplnia "
          "automaticky pri štarte (<font name='%s'>Storage._migrate</font>), takže používateľ nestratí "
          "nazbierané dáta. Najlepšiu cenu každej snímky vyberá SQL dotaz s window funkciou:" % MONO),
        code("""
SELECT ... FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY recorded_at ORDER BY price, store_id) AS rank_in_snapshot
    FROM price_history WHERE game_id = ?
) h WHERE h.rank_in_snapshot = 1 ORDER BY h.recorded_at
"""),
        h2("5.3 Integrácia s CheapShark API"),
        p("Používajú sa endpointy <i>/games</i> (vyhľadávanie a detail), <i>/deals</i> (aktuálne zľavy) a "
          "<i>/stores</i>. API vracia čísla ako reťazce, preto každá hodnota prechádza validáciou; "
          "neplatná odpoveď vyvolá výnimku <font name='%s'>ApiError</font> namiesto pádu programu. "
          "Timeout, kód 429 (limit požiadaviek), chyby 5xx a neplatný JSON majú vlastné zrozumiteľné "
          "správy. URL obrázkov sa akceptujú iba so schémou <i>https://</i>." % MONO),
        h2("5.4 Analýza a odporúčanie"),
        p("Modul <i>analysis.py</i> prevedie najlepšie ceny jednotlivých snímok na DataFrame a vypočíta "
          "štatistiky. Historické minimum kombinuje vlastné záznamy s minimom, ktoré hlási CheapShark – "
          "pokrýva teda aj obdobie pred začiatkom sledovania. Odporúčanie sa vyhodnocuje podľa "
          "pravidiel v tomto poradí:"),
        table([
            ["Verdikt", "Podmienka"],
            ["BUY NOW", "cena dosiahla cieľovú cenu, alebo je najviac 10 % nad historickým minimom"],
            ["GOOD DEAL", "zľava aspoň 50 %, alebo cena aspoň 15 % pod zaznamenaným priemerom"],
            ["WAIT", "hra už bola aspoň o 30 % lacnejšia, alebo momentálne nie je v zľave"],
            ["NO DATA", "zatiaľ neexistuje žiadna snímka ceny"],
        ], [3.0, 13.5], "Pravidlá odporúčania"),
        p("Pri menej ako troch snímkach sa k odporúčaniu pridá upozornenie na nízku spoľahlivosť. "
          "Prahy sú konštanty na začiatku modulu. Pravidlá zámerne vysvetľujú minulé ceny a "
          "netvrdia, že predpovedajú budúce výpredaje."),
        h2("5.5 REST API"),
        table([
            ["Metóda a cesta", "Popis", "Kódy"],
            ["GET /api/dashboard", "súhrn, najväčšia zľava, udalosti", "200"],
            ["GET /api/wishlist", "sledované hry s cenou, stavom a odporúčaním", "200"],
            ["POST /api/wishlist", "pridanie hry {game_id, target_price}", "201, 409, 422, 502"],
            ["DELETE /api/wishlist/{id}", "zrušenie sledovania", "204, 404"],
            ["PUT /api/wishlist/{id}/target", "nastavenie alebo zrušenie cieľovej ceny", "200, 404, 422"],
            ["GET /api/games/{id}", "detail: štatistiky, história, ponuky obchodov", "200, 404"],
            ["POST /api/update", "kontrola cien {force}", "200"],
            ["GET /api/search, /api/deals", "vyhľadávanie hier, aktuálne zľavy s filtrami", "200, 422, 502"],
            ["GET /api/stores, /api/meta", "obchody; verzia, kurzy mien, zdroje dát", "200"],
        ], [5.0, 8.3, 3.2], "Endpointy REST API (ceny sú v USD)", keep=False),
        p("Chybu externého API mapuje handler na kód 502 s textom chyby, neplatný vstup odmietne "
          "Pydantic kódom 422. Frontend tieto správy zobrazuje používateľovi."),
        h2("5.6 Webové rozhranie"),
        p("Frontend je jednostránková aplikácia bez build kroku – súbory servuje priamo FastAPI. "
          "Kód je rozdelený do ES modulov: <i>api.js</i> (komunikácia so serverom), <i>format.js</i> "
          "(formátovanie a prevod mien), <i>charts.js</i> (vlastné SVG grafy s tooltipom), <i>ui.js</i> "
          "(modálne okná, notifikácie) a samostatné moduly pre každú stránku. Všetok text z API "
          "prechádza funkciou <font name='%s'>esc()</font>, ktorá bráni vloženiu HTML (XSS). "
          "Pri prechode medzi stránkami kontroluje funkcia <font name='%s'>active()</font>, či "
          "odpoveď ešte patrí k aktuálnej stránke, takže pomalá odpoveď neprepíše novú stránku. "
          "Preferencie (mena, rozloženie) sa ukladajú do localStorage." % (MONO, MONO)),
        h2("5.7 Desktopová aplikácia a meny"),
        p("Tkinter dovoľuje meniť okná iba z hlavného vlákna. HTTP požiadavky preto bežia v "
          "ThreadPoolExecutor a výsledok sa preberá periodicky cez <font name='%s'>after()</font> "
          "(modul <i>ui/background.py</i>). Kurzy mien drží <i>currency.py</i> v pamäti 12 hodín; "
          "prístup chráni zámok, pretože web server obsluhuje požiadavky paralelne. Ak služba "
          "nie je dostupná, použijú sa posledné známe kurzy, prípadne iba USD." % MONO),
        h2("5.8 Synchronizácia s cloudom (sync.py)"),
        p("Workflow <i>.github/workflows/collect-prices.yml</i> beží každých 6 hodín (aj ručne cez tlačidlo "
          "<i>Run workflow</i>). Zoznam hier berie zo súboru <i>wishlist.json</i>, databázu obnoví z vetvy "
          "<i>data</i>, skontroluje ceny a databázu uloží späť ako jediný commit. Lokálna strana "
          "stiahne súbor <i>game_tracker.db</i> a funkcia <font name='%s'>merge_remote_database</font> "
          "pridá iba snímky, ktoré lokálna databáza ešte nemá. Snímka sa identifikuje dvojicou "
          "(čas, obchod), takže zlúčenie je <b>idempotentné</b> – opakovaný beh nič nezmení a lokálne "
          "záznamy sa nikdy neprepíšu ani nezmažú. Stiahnutý súbor sa overuje (hlavička SQLite, "
          "limit veľkosti 50 MB) skôr, než sa použije." % MONO),
    ]


def section_testing() -> list:
    return [
        h1("6 Testovanie a robustnosť"),
        p("Projekt obsahuje 120 automatických testov (pytest). Žiadny test nepoužíva internet: "
          "externé API nahrádza <font name='%s'>httpx.MockTransport</font> alebo falošný zdroj dát, "
          "databáza vzniká v dočasnom adresári (<font name='%s'>tmp_path</font>) a REST API sa testuje "
          "cez <font name='%s'>TestClient</font> z FastAPI." % (MONO, MONO, MONO)),
        table([
            ["Súbor", "Počet", "Čo overuje"],
            ["test_api_client.py", "11", "parsovanie odpovedí, timeout, 429, 500, neplatné čísla, nebezpečné URL"],
            ["test_storage.py", "12", "wishlist, snímky, najlepšia cena, kaskádové mazanie, migrácia, SQL injection"],
            ["test_analysis.py", "10", "štatistiky a všetky vetvy odporúčania vrátane hry zadarmo"],
            ["test_collector.py", "7", "interval snímok, --force, upozornenia, zlyhanie jednej hry"],
            ["test_sync.py", "14", "wishlist.json, zlúčenie snímok (idempotencia), sťahovanie, neplatný súbor"],
            ["test_web_api.py", "16", "endpointy, stavové kódy 201/204/404/409/422/502, validácia"],
            ["test_insights.py", "5", "stav cieľa, udalosti, súhrn dashboardu"],
            ["test_currency.py", "5", "kurzy, cache a jej expirácia, výpadok služby"],
            ["ostatné (5 súborov)", "27", "konfigurácia, služba, grafy, formátovanie GUI, súbory frontendu"],
        ], [4.0, 1.4, 11.1], "Prehľad automatických testov", keep=False),
        h2("6.1 Chybové situácie"),
        table([
            ["Situácia", "Správanie aplikácie"],
            ["CheapShark neodpovedá / timeout", "zrozumiteľná správa (502 vo webe), aplikácia beží ďalej"],
            ["prekročený limit požiadaviek (429)", "správa „skúste neskôr“"],
            ["zlyhá aktualizácia jednej hry", "ostatné hry sa aktualizujú, chyba je v reporte"],
            ["nedostupné kurzy mien", "posledné známe kurzy, inak zobrazenie v USD"],
            ["neplatný vstup (záporná cena, text)", "odmietnutie vo frontende aj v API (422)"],
            ["pridanie už sledovanej hry", "kód 409, frontend ukáže stav „Tracked“"],
            ["stará databáza z verzie 0.1", "automatická migrácia, údaje sa zachovajú"],
            ["cloudová databáza chýba alebo je poškodená", "zrozumiteľná správa, lokálne dáta sa nezmenia"],
            ["chýbajúci obrázok hry", "náhradný obrázok, potom názov hry"],
        ], [6.0, 10.5], "Ošetrenie chybových situácií"),
        h2("6.2 Kvalita kódu"),
        p("Kvalitu kódu kontrolujú dva nástroje, nastavené v <i>pyproject.toml</i>. "
          "<font name='%s'>ruff check src tests</font> (pravidlá E, F, W, I, B, UP) hlási "
          "<i>All checks passed</i>; <font name='%s'>mypy src/game_tracker</font> hlási "
          "<i>no issues found in 27 source files</i>. Type hints sú použité v celom verejnom API "
          "projektu. Pri kontrole sa našlo napríklad nesprávne ošetrenie hodnoty None v súhrne "
          "dashboardu, ktoré sa opravilo. Rovnaké tri kontroly (ruff, mypy, pytest) bežia automaticky pri "
          "každom pushi v GitHub Actions (workflow <i>tests.yml</i>)." % (MONO, MONO)),
        h2("6.3 Manuálne overenie"),
        p("Webové rozhranie bolo overené v prehliadači týmito scenármi: pridanie hry cez modálne okno "
          "aj globálne vyhľadávanie, zamedzenie duplicity, uloženie cieľovej ceny (aj s desatinnou "
          "čiarkou), odmietnutie neplatnej ceny, prepínanie rozsahu grafu a tooltip, filtre, "
          "triedenie a rozloženie wishlistu, odstránenie hry s potvrdením, filtre stránky Discover, "
          "zmena meny a jej uloženie po obnovení stránky, notifikácie, nastavenia a stránka "
          "neexistujúcej hry. Pri overovaní sa našli a opravili štyri chyby, napr. neuloženie "
          "cieľovej ceny pri vypnutom prepínači upozornení."),
    ]


def section_security() -> list:
    return [
        h1("7 Bezpečnosť"),
        *bullets([
            "<b>Sieť</b> – web server počúva iba na 127.0.0.1, nie je dostupný z iných zariadení.",
            "<b>SQL</b> – všetky dotazy používajú parametre (?); test overuje názov hry s textom "
            "<font name='%s'>'); DROP TABLE games;--</font>." % MONO,
            "<b>Vstupy</b> – Pydantic kontroluje typy a rozsahy (game_id &gt; 0, cena 0 až 10 000, "
            "dĺžka hľadaného textu), CLI a GUI majú vlastnú validáciu.",
            "<b>XSS</b> – text z externých API sa vo frontende vždy escapuje; obrázky sa prijímajú "
            "iba z adries https.",
            "<b>Secrets</b> – projekt nepotrebuje API kľúče; konfigurácia je v .env, ktorý je v .gitignore. "
            "Voliteľný token pre súkromný repozitár (GT_SYNC_TOKEN) žije iba tam.",
            "<b>Cloud</b> – workflow používa iba vstavaný GITHUB_TOKEN s právom zápisu do repozitára; "
            "stiahnutá databáza sa pred použitím overuje a zlučuje sa iba pridávaním chýbajúcich riadkov.",
            "<b>Externé služby</b> – každá HTTP požiadavka má timeout; odpovede sa validujú.",
            "<b>Súborový systém</b> – cesty cez pathlib, relatívne voči projektu, žiadne absolútne cesty v kóde.",
        ]),
    ]


def section_usage() -> list:
    return [
        h1("8 Použitie programu"),
        h2("8.1 Inštalácia a spustenie"),
        p("Požiadavky: Python 3.10 alebo novší, internetové pripojenie a webový prehliadač."),
        code("""
python -m venv .venv
.venv\\Scripts\\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest                             # 120 passed
ruff check src tests               # All checks passed
mypy src/game_tracker              # Success: no issues found
game-tracker web                   # otvorí http://127.0.0.1:8000
"""),
        p("Nastavenia (port, interval kontroly cien, cesta k databáze, URL API) sú v súbore .env – "
          "vzor je v <i>.env.example</i>. Všetky hodnoty majú predvolené nastavenie, takže aplikácia "
          "funguje aj bez neho. Databáza sa vytvorí automaticky."),
        h2("8.2 Webová aplikácia"),
        p("Prehľad (Overview) zobrazuje súhrnné čísla, hru s najväčšou zľavou, sledované hry a "
          "posledné zmeny cien. Hru pridáte tlačidlom <i>Track a game</i>."),
        figure("web_overview.png", "Prehľad – dashboard", 12.5),
        figure("web_game.png", "Detail hry – graf ceny, porovnanie obchodov, odporúčanie a cieľová cena", 12.5),
        figure("web_game_light.png", "Rovnaký detail v svetlej téme (prepínač v hornej lište)", 11.5),
        figure("web_wishlist.png", "Wishlist – vyhľadávanie, filtre, triedenie a stav cieľovej ceny", 12.5),
        figure("web_discover.png", "Discover – aktuálne zľavy s filtrami", 11.5),
        h2("8.3 Desktopová aplikácia a CLI"),
        figure("desktop_gui.png", "Desktopová aplikácia (Tkinter)", 11.5),
        code("""
game-tracker search "hollow knight"     # vyhľadanie hry a jej ID
game-tracker add 165363 --target 10     # sledovanie s cieľovou cenou (USD)
game-tracker list                       # wishlist s cenami a odporúčaním
game-tracker update                     # kontrola cien (--force ignoruje interval)
game-tracker stats 165363               # štatistiky a odporúčanie
game-tracker chart 165363 --open        # graf ako PNG
"""),
        h2("8.4 Zber cien v cloude"),
        p("Jednorazové nastavenie: v súbore .env nastaviť <font name='%s'>GT_SYNC_REPO=vlastník/repozitár</font>, "
          "spustiť <font name='%s'>game-tracker sync --push</font> a na GitHube v záložke Actions spustiť "
          "workflow <i>Collect prices</i>. Ďalej sa ceny zbierajú automaticky a "
          "<font name='%s'>game-tracker web</font> ich pri štarte zlúči s lokálnou databázou. Po pridaní alebo "
          "odstránení hier treba znova spustiť <font name='%s'>sync --push</font>." % (MONO, MONO, MONO, MONO)),
    ]


def section_lessons() -> list:
    return [
        h1("9 Čo som sa naučil"),
        p("Najviac som sa naučil o <b>návrhu aplikácie vo vrstvách</b>. Na začiatku bol projekt iba CLI. "
          "Keď som pridával desktopové a neskôr webové rozhranie, ukázalo sa, že logika musí byť "
          "oddelená od rozhrania – inak by som rovnaký výpočet písal trikrát. Moduly <i>overview.py</i> "
          "a <i>service.py</i> vznikli práve pri tejto refaktorizácii."),
        p("Prakticky som riešil <b>prácu s vláknami</b>: Tkinter aj FastAPI spracúvajú požiadavky "
          "paralelne, pričom spojenie sqlite3 sa nesmie zdieľať medzi vláknami. Ďalej som sa naučil "
          "písať testy, ktoré nezávisia od internetu (mockovanie HTTP, vkladanie závislostí), a "
          "navrhnúť <b>migráciu databázy</b>, aby používateľ pri aktualizácii nestratil dáta."),
        p("Zaujímavým problémom bola <b>synchronizácia s cloudom</b>. Obojsmerné kopírovanie databázy by "
          "viedlo ku konfliktom, preto som určil jedného vlastníka každého údaju: zoznam hier posiela "
          "počítač (wishlist.json), nové ceny posiela cloud a lokálne sa iba pridávajú. Zlúčenie som "
          "navrhol idempotentne, aby sa dalo bezpečne spúšťať opakovane."),
        p("Zaujímavou chybou bolo, že hry pridané v prvej verzii nemali historické minimum, a keďže "
          "aktualizácia hry s čerstvou snímkou sa preskakovala, odporúčanie zostávalo nesprávne. "
          "Opravil som to a pridal regresný test."),
        p("Nabudúce by som od začiatku navrhol <b>API vrstvu</b> a spoločnú aplikačnú službu, "
          "skôr nastavil automatické spúšťanie testov (napr. GitHub Actions) a zbieranie cien by som "
          "spustil hneď v prvý deň, aby bolo na analýzu viac historických dát."),
    ]


def section_limits() -> list:
    return [
        h1("10 Obmedzenia a možné rozšírenia"),
        h2("10.1 Obmedzenia"),
        *bullets([
            "ceny sa zbierajú každých 6 hodín; GitHub môže spustenie oneskoriť o niekoľko minút a "
            "plánované workflow v repozitári bez aktivity po 60 dňoch pozastaví,",
            "história je krátka – pokrýva iba čas sledovania, preto sa kombinuje s minimom z CheapShark,",
            "CheapShark pokrýva PC obchody a ceny v USD; prepočet na EUR je orientačný (kurz ECB, nie cena obchodu),",
            "upozornenia sa zobrazujú iba v aplikácii (bez e-mailu alebo push notifikácií),",
            "aplikácia je určená pre jedného používateľa na lokálnom počítači.",
        ]),
        h2("10.2 Možné rozšírenia"),
        *bullets([
            "hosting webovej aplikácie na serveri s heslom, aby bola dostupná aj z mobilu,",
            "e-mailové alebo systémové notifikácie pri dosiahnutí cieľovej ceny,",
            "kolekcie hier a viacero používateľov s prihlásením,",
            "ceny priamo v eurách z obchodov, ktoré ich poskytujú,",
            "lepší model odporúčania (napr. sezónnosť výpredajov) po nazbieraní dlhšej histórie.",
        ]),
    ]


def section_sources() -> list:
    return [
        h1("11 Zdroje a použité nástroje"),
        *bullets([
            "CheapShark API – dokumentácia: https://apidocs.cheapshark.com",
            "Frankfurter API (referenčné kurzy ECB): https://frankfurter.dev",
            "dokumentácie: Python (sqlite3, argparse, tkinter, concurrent.futures), httpx, pandas, "
            "matplotlib, FastAPI, Pydantic, uvicorn, pytest, ReportLab",
            "ikony Lucide (licencia ISC): https://lucide.dev; obrázky hier zo Steam CDN",
            "materiály predmetu Programovanie v Pythone: https://marek-horvath.github.io/python/",
        ]),
        h2("11.1 Použitie AI nástrojov"),
        p("Pri projekte som používal AI asistenta <b>Claude</b> (Anthropic). Pomáhal mi s výberom a "
          "návrhom témy, s návrhom architektúry, s generovaním častí zdrojového kódu (backend, "
          "webové rozhranie, testy), s hľadaním chýb a s prípravou textu tejto dokumentácie. "
          "Vygenerovaný kód som spúšťal, testoval na vlastnom počítači s reálnymi dátami (pytest, ruff, "
          "mypy), prechádzal a upravoval. Rozumiem fungovaniu všetkých modulov a viem vysvetliť technické rozhodnutia "
          "opísané v tejto dokumentácii."),
    ]


def build() -> None:
    IMG.mkdir(exist_ok=True)
    build_architecture_diagram(IMG / "architecture.png")

    doc = DocTemplate(str(OUTPUT), pagesize=A4, title=PROJECT_TITLE, author=AUTHOR,
                      leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.0 * cm,
                      bottomMargin=2.2 * cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[frame]),
        PageTemplate(id="content", frames=[frame], onPage=on_page),
    ])
    story = [*title_page(), *contents()]
    for section in (section_intro, section_requirements, section_design, section_technologies,
                    section_implementation, section_testing, section_security, section_usage,
                    section_lessons, section_limits, section_sources):
        story += list(flatten(section()))
    doc.multiBuild(story)
    print(f"Documentation written to {OUTPUT}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate docs/documentation.pdf")
    parser.add_argument("--author", default=AUTHOR, help="your name for the title page")
    parser.add_argument("--year", default=ACADEMIC_YEAR, help='academic year, e.g. "2026/2027"')
    parser.add_argument("--repo", default=REPOSITORY, help="repository URL")
    args = parser.parse_args()
    globals().update(AUTHOR=args.author, ACADEMIC_YEAR=args.year, REPOSITORY=args.repo)
    if args.author == "Meno Priezvisko":
        print('WARNING: the author is still a placeholder. Use: --author "Ivan Nerodyk"')
    build()


if __name__ == "__main__":
    main()
