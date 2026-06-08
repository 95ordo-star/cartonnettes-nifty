#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stop_rayons.py
==============
Récupère tous les stop-rayons Nifty du mois en cours (page /offres/) et les
assemble TELS QUELS dans un seul PDF (aucun redimensionnement, les pages gardent
leur format d'origine).

Utilisation :
    python stop_rayons.py
    python stop_rayons.py --sortie Stop-rayons-Nifty.pdf
    python stop_rayons.py --urls-file mes_liens.txt
"""

import argparse
import datetime as dt
import os
import re
import sys
import urllib.request

try:
    import fitz  # PyMuPDF
except ImportError as e:
    sys.exit("Dépendance manquante (%s). Installez : pip install pymupdf" % e)

OFFRES_URL = "https://nifty.highco.com/offres/"
UA = {"User-Agent": "Mozilla/5.0 (stop-rayons)"}


def decouvrir_urls(offres_url=OFFRES_URL):
    req = urllib.request.Request(offres_url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "ignore")
    liens = re.findall(
        r"https://nifty\.highco\.com/wp-content/uploads/[^\"'<> ]*\.pdf", html
    )
    return sorted({u for u in liens if "Stop-rayon" in u})


def lire_urls_fichier(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def fusionner(urls, sortie):
    out = fitz.open()
    nb = 0
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if not data.startswith(b"%PDF"):
                print("  ! ignoré (pas un PDF) : %s" % url)
                continue
        except Exception as exc:
            print("  ! échec %s (%s)" % (url, exc))
            continue
        src = fitz.open(stream=data, filetype="pdf")
        out.insert_pdf(src)          # ajoute les pages telles quelles
        print("  OK  %s (%d page(s))" % (os.path.basename(url), src.page_count))
        nb += 1
        src.close()
    out.save(sortie, deflate=True, garbage=4)
    pages = out.page_count
    out.close()
    return nb, pages


def main():
    p = argparse.ArgumentParser(description="Fusionne les stop-rayons Nifty du mois en un PDF.")
    p.add_argument("--urls-file")
    p.add_argument("--offres-url", default=OFFRES_URL)
    p.add_argument("--sortie")
    args = p.parse_args()

    urls = lire_urls_fichier(args.urls_file) if args.urls_file else decouvrir_urls(args.offres_url)
    if not urls:
        sys.exit("Aucun stop-rayon trouvé.")
    print("%d stop-rayon(s) à assembler :" % len(urls))

    sortie = args.sortie or "Stop-rayons-Nifty-%s.pdf" % dt.date.today().strftime("%Y-%m")
    nb, pages = fusionner(urls, sortie)
    print("\nTerminé : %s  (%d fichiers, %d pages)" % (sortie, nb, pages))
    print("Emplacement : %s" % os.path.abspath(sortie))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code:
            print("\nErreur : %s" % e.code)
    if getattr(sys, "frozen", False):
        input("\nAppuyez sur Entrée pour fermer...")
