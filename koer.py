"""Kører hele beregningen og skriver resultater og figurer."""

import pandas as pd

import data
import figurer
import model


def main() -> None:
    print("indlæser data")
    panel = data.byg_panel()
    print(f"  {len(panel):,} observationer, {panel['valuta'].nunique()} valutaer, "
          f"{panel['maaned'].min()} til {panel['maaned'].max()}")

    print("laver rullende prognoser")
    tabel, prognoser = model.koer_alle(panel)
    fortegn = model.fortegn_i_fuld_stikproeve(panel)

    tabel.to_csv("resultater.csv", index=False)
    prognoser.to_csv("prognoser.csv", index=False)
    fortegn.to_csv("fortegn.csv", index=False)

    print("tegner figurer")
    for sti in figurer.lav_alle(panel):
        print(f"  {sti.name}")

    slaar = tabel[tabel["r2_vs_random_walk_pct"] > 0]
    print(f"\n{len(slaar)} af {len(tabel)} modeller slår random walk:")
    if len(slaar):
        print(slaar.sort_values("r2_vs_random_walk_pct", ascending=False)
              .to_string(index=False))
    print("\nresultater.csv, prognoser.csv, fortegn.csv skrevet")


if __name__ == "__main__":
    main()
