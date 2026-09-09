"""Indlæsning af data og opbygning af de fire variable.

Alle serier er månedlige. Valutakurserne er noteret som udenlandsk valuta per
dollar, så en stigning betyder en stærkere dollar. Det gælder også for
Australien og Storbritannien, hvor markedet ellers normalt noterer omvendt.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"

# Tre råvarevalutaer og to kontrolvalutaer. De sidste to har ingen oplagt
# forbindelse til olieprisen og er med for at vise, hvad et nulresultat ligner.
VALUTAER = {
    "Norway": "NOK",
    "Canada": "CAD",
    "Australia": "AUD",
    "Japan": "JPY",
    "Switzerland": "CHF",
}

RAAVAREVALUTAER = ["NOK", "CAD", "AUD"]

# Fortegnene skrives ned her, før modellerne køres.
# Målet er ændringen i udenlandsk valuta per dollar, så positivt fortegn
# betyder "denne variabel varsler en stærkere dollar".
FORVENTEDE_FORTEGN = {
    "olie": {
        "raavare": -1,   # dyrere olie styrker råvarevalutaen, altså svagere dollar
        "kontrol": +1,   # Japan og Schweiz importerer olie, så dyrere olie svækker dem
    },
    "momentum": +1,      # trends i valuta har historisk haft en tendens til at fortsætte
    "afvigelse": -1,     # kurser langt fra deres eget femårige gennemsnit trækker tilbage
    "usrente": +1,       # stigende amerikanske renter trækker kapital mod dollaren
}


def _maaned(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.to_period("M")


def indlaes_valuta() -> pd.DataFrame:
    raa = pd.read_csv(DATA / "monthly.csv")
    raa = raa[raa["Country"].isin(VALUTAER)].copy()
    raa["maaned"] = _maaned(raa["Date"])
    raa["valuta"] = raa["Country"].map(VALUTAER)
    bred = raa.pivot(index="maaned", columns="valuta", values="Exchange rate")
    return bred.sort_index()


def indlaes_olie() -> pd.Series:
    raa = pd.read_csv(DATA / "brent.csv")
    raa["maaned"] = _maaned(raa["Date"])
    return raa.set_index("maaned")["Price"].sort_index()


def indlaes_usrente(tolerance: float = 0.02) -> pd.Series:
    """Amerikansk 10-årig rente, månedlig.

    Kildefilen indeholder den samme serie stablet flere gange. For de fleste
    måneder er kopierne identiske. Seks måneder afviger med 0,01 procentpoint,
    hvilket er afrunding mellem to opgørelser, og der tages medianen. Den
    sidste måned i filen afviger med 0,21 og er en ufuldstændig opgørelse;
    måneder med reel uenighed kasseres i stedet for at blive gættet.
    """
    raa = pd.read_csv(DATA / "us10y.csv")
    raa["maaned"] = pd.PeriodIndex(raa["Date"], freq="M")

    spredning = raa.groupby("maaned")["Yield"].agg(lambda x: x.max() - x.min())
    kasseret = spredning[spredning > tolerance].index
    if len(kasseret):
        print(f"  rente: kasserer {len(kasseret)} måned(er) med uenige kopier: "
              f"{', '.join(str(m) for m in kasseret)}")

    serie = raa[~raa["maaned"].isin(kasseret)].groupby("maaned")["Yield"].median()
    return serie.sort_index()


def byg_panel() -> pd.DataFrame:
    """Ét langt panel med en række per valuta per måned.

    Kolonnen `maal` er næste måneds logændring i kursen. Alt andet er kendt
    ved udgangen af den måned, rækken står på. Der er ingen offentliggørelses-
    forsinkelse at tage højde for: olieprisen, den amerikanske rente og
    valutakursen er alle markedspriser, man kunne aflæse samme dag. Det er
    forskellen fra en model på inflationstal, hvor tallet for en måned først
    kommer måneden efter.
    """
    fx = indlaes_valuta()
    olie = indlaes_olie()
    rente = indlaes_usrente()

    olie_aendring = np.log(olie).diff()
    rente_aendring = rente.diff()

    raekker = []
    for valuta in fx.columns:
        kurs = fx[valuta].dropna()
        log_kurs = np.log(kurs)
        aendring = log_kurs.diff()

        d = pd.DataFrame(index=kurs.index)
        d["valuta"] = valuta
        d["kurs"] = kurs
        d["maal"] = aendring.shift(-1)                       # næste måneds ændring
        d["olie"] = olie_aendring.reindex(kurs.index)
        d["momentum"] = log_kurs - log_kurs.shift(12)
        d["afvigelse"] = log_kurs - log_kurs.rolling(60).mean()
        d["usrente"] = rente_aendring.reindex(kurs.index)
        raekker.append(d)

    panel = pd.concat(raekker).reset_index().rename(columns={"index": "maaned"})
    panel = panel.dropna(subset=["maal", "olie", "momentum", "afvigelse", "usrente"])
    return panel.sort_values(["valuta", "maaned"]).reset_index(drop=True)


VARIABLE = ["olie", "momentum", "afvigelse", "usrente"]


def forventet_fortegn(variabel: str, valuta: str) -> int:
    if variabel == "olie":
        gruppe = "raavare" if valuta in RAAVAREVALUTAER else "kontrol"
        return FORVENTEDE_FORTEGN["olie"][gruppe]
    return FORVENTEDE_FORTEGN[variabel]
