"""Testene tjekker, at ingen model bruger data fra fremtiden."""

import numpy as np
import pandas as pd
import pytest

import data
import model


@pytest.fixture(scope="module")
def panel():
    return data.byg_panel()


def test_afkortet_datasaet_giver_samme_prognoser(panel):
    """Den vigtigste test.

    Beregningen køres to gange: en gang på det fulde datasæt og en gang på et
    datasæt, der er klippet af i 2010. Alle prognoser fra før 2010 skal være
    ens i de to kørsler. Hvis en model kiggede fremad, ville de afvige.
    """
    graense = pd.Period("2010-01", freq="M")
    afkortet = panel[panel["maaned"] < graense]

    for valuta in ["NOK", "JPY"]:
        fuld = model.rullende_prognoser(panel, valuta, data.VARIABLE)
        kort = model.rullende_prognoser(afkortet, valuta, data.VARIABLE)
        faelles = kort["maaned"].max()

        a = fuld[fuld["maaned"] <= faelles].set_index("maaned")["prognose"]
        b = kort[kort["maaned"] <= faelles].set_index("maaned")["prognose"]
        assert len(b) > 50
        np.testing.assert_allclose(a.loc[b.index], b, rtol=1e-10)


def test_maalet_er_naeste_maaneds_aendring(panel):
    """`maal` skal være ændringen fra denne måned til den næste, ikke fra
    forrige til denne."""
    d = panel[panel["valuta"] == "NOK"].sort_values("maaned").reset_index(drop=True)
    beregnet = np.log(d["kurs"].shift(-1)) - np.log(d["kurs"])
    naeste_maaned_foelger = d["maaned"].shift(-1) == d["maaned"] + 1

    gyldig = naeste_maaned_foelger & beregnet.notna()
    assert gyldig.sum() > 300
    np.testing.assert_allclose(d.loc[gyldig, "maal"],
                               beregnet[gyldig], atol=1e-12)


def test_ingen_variabel_korrelerer_mistaenkeligt_med_maalet(panel):
    """En variabel, der forudsiger næste måned med korrelation over 0,3, ville
    være for godt til at være sandt på månedlige valutadata."""
    for valuta in panel["valuta"].unique():
        d = panel[panel["valuta"] == valuta]
        for variabel in data.VARIABLE:
            r = abs(d[variabel].corr(d["maal"]))
            assert r < 0.3, f"{valuta}/{variabel} korrelerer {r:.2f} med målet"


def test_prognoser_bruger_kun_fortid(panel):
    """Antallet af prognoser skal svare til observationer minus estimations-
    vinduet, så den første prognose ikke er lavet på sit eget data."""
    d = panel[panel["valuta"] == "CAD"]
    p = model.rullende_prognoser(panel, "CAD", data.VARIABLE)
    assert len(p) == len(d) - model.MINIMUM_ESTIMATION
    assert p["maaned"].min() > d["maaned"].min()


def test_renten_har_ingen_dubletter():
    r = data.indlaes_usrente()
    assert not r.index.duplicated().any()
    assert r.index.is_monotonic_increasing
