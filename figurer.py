"""De to figurer."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data import RAAVAREVALUTAER, VARIABLE, forventet_fortegn
from model import rullende_prognoser

FIGURER = Path(__file__).resolve().parent / "figurer"
FARVER = {"NOK": "#1f4e79", "CAD": "#2e7d32", "AUD": "#7b4fa8",
          "JPY": "#b03030", "CHF": "#a0721b"}


def _stil(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)


def figur_kumuleret_fejl(panel: pd.DataFrame) -> Path:
    """Fejlforskellen mod random walk lagt sammen måned for måned.

    Over nul betyder, at oliemodellen indtil da har haft mindre samlet fejl
    end en random walk. Kurven viser, hvornår det skete, i stedet for kun at
    give ét tal for hele perioden.
    """
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    for valuta in ["NOK", "CAD", "AUD", "JPY", "CHF"]:
        p = rullende_prognoser(panel, valuta, ["olie"])
        if p.empty:
            continue
        fordel = (p["faktisk"] ** 2 - (p["faktisk"] - p["prognose"]) ** 2).cumsum()
        x = p["maaned"].dt.to_timestamp()
        stil = "-" if valuta in RAAVAREVALUTAER else "--"
        ax.plot(x, fordel * 1e4, stil, color=FARVER[valuta], linewidth=1.4,
                label=f"{valuta}{'' if valuta in RAAVAREVALUTAER else ' (kontrol)'}")
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_ylabel("kumuleret fejlfordel mod random walk", fontsize=8.5)
    ax.legend(fontsize=8, frameon=False, ncol=5, loc="upper left")
    _stil(ax)
    fig.tight_layout()
    sti = FIGURER / "figur1_kumuleret_fejl.png"
    fig.savefig(sti, bbox_inches="tight")
    plt.close(fig)
    return sti


def figur_saadan_virker_den(panel: pd.DataFrame) -> Path:
    """Olieprisændring mod næste måneds kursændring, en rude per valuta."""
    valutaer = ["NOK", "CAD", "AUD", "JPY", "CHF"]
    fig, akser = plt.subplots(1, len(valutaer), figsize=(13, 2.9), dpi=150,
                              sharey=True)
    for ax, valuta in zip(akser, valutaer):
        d = panel[panel["valuta"] == valuta]
        x, y = d["olie"].to_numpy(), d["maal"].to_numpy()
        ax.scatter(x * 100, y * 100, s=5, alpha=0.28, color=FARVER[valuta],
                   linewidths=0)
        b = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs * 100, np.polyval(b, xs) * 100, color="#111", linewidth=1.2)
        ax.axhline(0, color="#999", linewidth=0.5)
        ax.axvline(0, color="#999", linewidth=0.5)
        mrk = "råvarevaluta" if valuta in RAAVAREVALUTAER else "kontrol"
        ax.set_title(f"{valuta} · {mrk}\nhældning {b[0]:.3f}", fontsize=8.5)
        ax.set_xlabel("olieprisændring, pct.", fontsize=8)
        _stil(ax)
    akser[0].set_ylabel("næste måneds kursændring, pct.", fontsize=8)
    fig.tight_layout()
    sti = FIGURER / "figur2_saadan_virker_den.png"
    fig.savefig(sti, bbox_inches="tight")
    plt.close(fig)
    return sti


def lav_alle(panel: pd.DataFrame):
    FIGURER.mkdir(exist_ok=True)
    return [figur_kumuleret_fejl(panel), figur_saadan_virker_den(panel)]
