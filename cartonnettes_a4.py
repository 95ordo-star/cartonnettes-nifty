#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cartonnettes_a4.py
==================
Génère automatiquement, chaque mois, un PDF regroupant toutes les cartonnettes
Nifty du moment, chacune agrandie pour remplir une page A4 (portrait par défaut),
en conservant les proportions et la qualité vectorielle (QR codes nets).

Ce que fait le script :
  1. Récupère la liste des cartonnettes du mois sur la page https://nifty.highco.com/offres/
     (découverte automatique des liens "Cartonnette-….pdf").
  2. Télécharge chaque PDF.
  3. Détecte chaque carte sur la planche (en supprimant les marges blanches),
     dédoublonne les exemplaires identiques, et gère les planches multi-cartes
     (ex. P&G qui contient plusieurs marques distinctes).
  4. Agrandit chaque carte pour remplir une page A4, sans déformation.
  5. Assemble le tout dans un seul PDF daté.

PRÉREQUIS (à installer une seule fois) :
    pip install pymupdf pillow numpy

UTILISATION :
    python cartonnettes_a4.py
        -> découvre les cartonnettes du mois et crée Cartonnettes-A4-portrait-AAAA-MM.pdf

    python cartonnettes_a4.py --orientation paysage
        -> version A4 paysage

    python cartonnettes_a4.py --urls-file mes_liens.txt
        -> utilise une liste d'URL fournie (1 URL par ligne) au lieu de la découverte auto

    python cartonnettes_a4.py --garder-doublons
        -> conserve les 2 exemplaires identiques de chaque carte (pas de dédoublonnage)

    python cartonnettes_a4.py --sortie /chemin/vers/fichier.pdf
"""

import argparse
import datetime as dt
import io
import os
import re
import sys
import urllib.request

# --- Dépendances tierces ---------------------------------------------------
try:
    import fitz  # PyMuPDF
    import numpy as np
    from PIL import Image
except ImportError as e:
    sys.exit(
        "Dépendance manquante (%s).\n"
        "Installez-les avec :  pip install pymupdf pillow numpy" % e
    )

# --- Paramètres (modifiables) ---------------------------------------------
OFFRES_URL = "https://nifty.highco.com/offres/"
DPI = 200          # résolution d'analyse (détection des cartes)
THRESH = 244       # seuil "blanc" : un pixel < 244 est considéré comme du contenu
MINGAP = 24        # largeur min (px) d'un espace blanc séparant deux cartes
CARD_RATIO = 0.70  # ratio largeur/hauteur d'une cartonnette unitaire (portrait)
DUP_TOL = 0.05     # tolérance de similarité pour considérer 2 cartes identiques
MARGIN = 14.17     # marge de sécurité (~0,5 cm) autour du visuel sur la page A4

A4 = {
    "portrait": (595.28, 841.89),
    "paysage":  (841.89, 595.28),
}

UA = {"User-Agent": "Mozilla/5.0 (cartonnettes_a4 script)"}


# --- 1) Découverte des URL -------------------------------------------------
def decouvrir_urls(offres_url=OFFRES_URL):
    """Scrute la page /offres/ et renvoie la liste triée des PDF Cartonnette-…"""
    req = urllib.request.Request(offres_url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "ignore")
    liens = re.findall(
        r'https://nifty\.highco\.com/wp-content/uploads/[^"\'<> ]*\.pdf', html
    )
    cartonnettes = sorted({u for u in liens if "Cartonnette" in u})
    return cartonnettes


def lire_urls_fichier(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


# --- 2) Téléchargement -----------------------------------------------------
def telecharger(urls, dossier):
    os.makedirs(dossier, exist_ok=True)
    chemins = []
    for i, url in enumerate(urls, 1):
        nom = "%02d_%s" % (i, os.path.basename(url))
        dest = os.path.join(dossier, nom)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if not data.startswith(b"%PDF"):
                print("  ! Ignoré (pas un PDF) : %s" % url)
                continue
            with open(dest, "wb") as f:
                f.write(data)
            chemins.append(dest)
            print("  OK  %s" % nom)
        except Exception as exc:
            print("  ! Échec %s (%s)" % (url, exc))
    return chemins


# --- 3) Détection des cartes ----------------------------------------------
def _segments(mask_1d, mingap):
    """Renvoie les plages d'indices "contenu" séparées par des trous >= mingap."""
    idx = np.where(mask_1d)[0]
    if len(idx) == 0:
        return []
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev - 1 >= mingap:
            runs.append((start, prev))
            start = i
        prev = i
    runs.append((start, prev))
    return runs


def detecter_cartes(arr):
    """arr = masque booléen (True = pixel de contenu). Renvoie une liste de bbox px.

    - sépare les cartes par les espaces blancs (grille lignes/colonnes) ;
    - si deux cartes identiques sont collées (bloc anormalement large),
      n'en garde qu'un exemplaire.
    """
    cartes = []
    for x0, x1 in _segments(arr.any(axis=0), MINGAP):
        bande = arr[:, x0:x1 + 1]
        for y0, y1 in _segments(bande.any(axis=1), MINGAP):
            sous = arr[y0:y1 + 1, x0:x1 + 1]
            cols = np.where(sous.any(axis=0))[0]
            xx0, xx1 = x0 + int(cols.min()), x0 + int(cols.max())
            w, h = xx1 - xx0 + 1, y1 - y0 + 1
            n = max(1, round((w / h) / CARD_RATIO))
            if n <= 1:
                cartes.append((xx0, y0, xx1, y1))
            else:
                # cartes collées (doublons) -> on ne garde que la première
                pas = w / n
                cartes.append((xx0, y0, int(round(xx0 + pas)) - 1, y1))
    cartes.sort(key=lambda b: (b[1] // 50, b[0]))  # ordre de lecture
    return cartes


def _vignette(arr, b):
    crop = arr[b[1]:b[3] + 1, b[0]:b[2] + 1].astype(np.uint8) * 255
    return np.asarray(Image.fromarray(crop).resize((40, 56))).astype(float) / 255


# --- 4 & 5) Construction du PDF -------------------------------------------
def construire_pdf(chemins_pdf, sortie, orientation, garder_doublons):
    A4_W, A4_H = A4[orientation]
    pts = 72.0 / DPI
    out = fitz.open()
    total = 0
    for chemin in chemins_pdf:
        src = fitz.open(chemin)
        png = src[0].get_pixmap(dpi=DPI).tobytes("png")
        arr = np.asarray(Image.open(io.BytesIO(png)).convert("L")) < THRESH
        cartes = detecter_cartes(arr)

        gardees, vignettes = [], []
        for b in cartes:
            if not garder_doublons:
                v = _vignette(arr, b)
                if any(np.abs(v - k).mean() < DUP_TOL for k in vignettes):
                    continue
                vignettes.append(v)
            gardees.append(b)

        for b in gardees:
            clip = fitz.Rect(b[0] * pts, b[1] * pts, (b[2] + 1) * pts, (b[3] + 1) * pts)
            cw, ch = clip.width, clip.height
            s = min((A4_W - 2 * MARGIN) / cw, (A4_H - 2 * MARGIN) / ch)
            tw, th = cw * s, ch * s
            tx, ty = (A4_W - tw) / 2, (A4_H - th) / 2
            page = out.new_page(width=A4_W, height=A4_H)
            page.show_pdf_page(fitz.Rect(tx, ty, tx + tw, ty + th), src, 0, clip=clip)

        print("  %-40s %d carte(s)" % (os.path.basename(chemin), len(gardees)))
        total += len(gardees)
        src.close()

    out.save(sortie, deflate=True, garbage=4)
    out.close()
    return total


# --- Programme principal ---------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Génère le PDF mensuel des cartonnettes Nifty au format A4.")
    p.add_argument("--orientation", choices=["portrait", "paysage"], default="portrait")
    p.add_argument("--urls-file", help="Fichier d'URL (1 par ligne) au lieu de la découverte auto")
    p.add_argument("--offres-url", default=OFFRES_URL, help="Page listant les offres")
    p.add_argument("--sortie", help="Chemin du PDF de sortie")
    p.add_argument("--garder-doublons", action="store_true",
                   help="Conserver les 2 exemplaires identiques de chaque carte")
    p.add_argument("--dossier-temp", default="_cartonnettes_dl",
                   help="Dossier de téléchargement temporaire")
    args = p.parse_args()

    # 1) URLs
    if args.urls_file:
        print("Lecture des URL depuis %s …" % args.urls_file)
        urls = lire_urls_fichier(args.urls_file)
    else:
        print("Découverte des cartonnettes sur %s …" % args.offres_url)
        urls = decouvrir_urls(args.offres_url)
    if not urls:
        sys.exit("Aucune cartonnette trouvée. Vérifiez la connexion ou la page /offres/.")
    print("%d cartonnette(s) à traiter.\n" % len(urls))

    # 2) Téléchargement
    print("Téléchargement :")
    chemins = telecharger(urls, args.dossier_temp)
    if not chemins:
        sys.exit("Aucun PDF téléchargé.")

    # 3-5) Construction
    sortie = args.sortie or "Cartonnettes-A4-%s-%s.pdf" % (
        args.orientation, dt.date.today().strftime("%Y-%m"))
    print("\nTraitement et mise en page (%s) :" % args.orientation)
    total = construire_pdf(chemins, sortie, args.orientation, args.garder_doublons)

    print("\nTerminé : %s  (%d pages)" % (sortie, total))
    print("Emplacement : %s" % os.path.abspath(sortie))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code:
            print("\nErreur : %s" % e.code)
    except Exception as e:
        print("\nErreur inattendue : %s" % e)
    # Si lancé en .exe (double-clic), garder la fenêtre ouverte pour lire le résultat
    if getattr(sys, "frozen", False):
        input("\nAppuyez sur Entrée pour fermer cette fenêtre...")
