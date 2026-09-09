"""Rullende prognoser og evaluering.

Referencen er en random walk: prognosen for næste måneds ændring er nul.
Det er den benchmark Meese og Rogoff brugte, og den er hårdere end det
historiske gennemsnit, fordi valutakurser stort set ingen drift har.
Begge rapporteres, så man kan se forskellen.
"""

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np
import pandas as pd

from data import VARIABLE

MINIMUM_ESTIMATION = 120   # ti år, før den første prognose laves


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Mindste kvadraters løsning med konstantled. lstsq frem for invers,
    så en næsten singulær designmatrix ikke giver et vildt resultat."""
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return beta


def rullende_prognoser(panel: pd.DataFrame, valuta: str,
                       variable: Sequence[str],
                       minimum: int = MINIMUM_ESTIMATION) -> pd.DataFrame:
    """Udvidende vindue: for hver måned estimeres modellen på alt, der ligger
    til og med den måned, og bruges til at forudsige den næste. Ingen
    observation indgår i estimationen af sin egen prognose."""
    d = panel[panel["valuta"] == valuta].sort_values("maaned").reset_index(drop=True)
    X_alle = d[list(variable)].to_numpy(float)
    y_alle = d["maal"].to_numpy(float)

    ud = []
    for t in range(minimum, len(d)):
        beta = _ols(X_alle[:t], y_alle[:t])
        prognose = float(beta[0] + X_alle[t] @ beta[1:])
        ud.append({
            "maaned": d["maaned"].iloc[t],
            "valuta": valuta,
            "faktisk": y_alle[t],
            "prognose": prognose,
            "gennemsnit": float(y_alle[:t].mean()),   # sekundær reference
        })
    return pd.DataFrame(ud)


@dataclass
class Resultat:
    valuta: str
    model: str
    n: int
    r2_rw: float          # ud-af-stikprøve R² mod random walk
    r2_gns: float         # samme, men mod det historiske gennemsnit
    retning: float        # andel måneder med rigtigt fortegn
    retning_rw: float     # samme for referencen, til sammenligning

    def raekke(self) -> List:
        return [self.valuta, self.model, self.n,
                round(self.r2_rw * 100, 2), round(self.r2_gns * 100, 2),
                round(self.retning * 100, 1), round(self.retning_rw * 100, 1)]


def evaluer(prog: pd.DataFrame, model: str) -> Resultat:
    faktisk = prog["faktisk"].to_numpy()
    model_fejl = ((faktisk - prog["prognose"]) ** 2).sum()
    rw_fejl = (faktisk ** 2).sum()                                  # random walk: nul
    gns_fejl = ((faktisk - prog["gennemsnit"]) ** 2).sum()

    # Random walk har ingen retning at ramme, så referencen for
    # retningskolonnen er andelen af måneder, hvor kursen faktisk steg.
    retning_rw = float((faktisk > 0).mean())
    retning = float((np.sign(prog["prognose"]) == np.sign(faktisk)).mean())

    return Resultat(
        valuta=prog["valuta"].iloc[0],
        model=model,
        n=len(prog),
        r2_rw=1 - model_fejl / rw_fejl,
        r2_gns=1 - model_fejl / gns_fejl,
        retning=retning,
        retning_rw=max(retning_rw, 1 - retning_rw),
    )


def koer_alle(panel: pd.DataFrame,
              minimum: int = MINIMUM_ESTIMATION):
    """Hver variabel for sig, og til sidst alle fire samlet."""
    resultater, alle_prognoser = [], []
    for valuta in sorted(panel["valuta"].unique()):
        for variabel in VARIABLE:
            p = rullende_prognoser(panel, valuta, [variabel], minimum)
            if p.empty:
                continue
            resultater.append(evaluer(p, variabel))
            p["model"] = variabel
            alle_prognoser.append(p)

        p = rullende_prognoser(panel, valuta, VARIABLE, minimum)
        if not p.empty:
            resultater.append(evaluer(p, "alle fire"))
            p["model"] = "alle fire"
            alle_prognoser.append(p)

    tabel = pd.DataFrame([r.raekke() for r in resultater], columns=[
        "valuta", "model", "n", "r2_vs_random_walk_pct",
        "r2_vs_gennemsnit_pct", "retning_pct", "retning_reference_pct"])
    return tabel, pd.concat(alle_prognoser, ignore_index=True)


def fortegn_i_fuld_stikproeve(panel: pd.DataFrame) -> pd.DataFrame:
    """Hældningen for hver variabel estimeret på hele perioden.

    Ikke en prognose — det er kun til at se, om sammenhængen overhovedet går
    den vej, jeg skrev ned på forhånd.
    """
    ud = []
    for valuta in sorted(panel["valuta"].unique()):
        d = panel[panel["valuta"] == valuta]
        for variabel in VARIABLE:
            beta = _ols(d[[variabel]].to_numpy(float), d["maal"].to_numpy(float))
            ud.append({"valuta": valuta, "variabel": variabel,
                       "haeldning": beta[1]})
    return pd.DataFrame(ud)
