# Cartonnettes Nifty — automatisation mensuelle (lien fixe)

Cette automatisation regénère **toute seule, le 1er de chaque mois**, le PDF des
cartonnettes Nifty (A4 portrait) et le publie à une **adresse fixe**.
Vous n'avez plus rien à lancer : il suffit d'ouvrir le lien quand vous voulez
le PDF du moment.

## Contenu
- `cartonnettes_a4.py` — le script de génération
- `requirements.txt` — dépendances
- `.github/workflows/cartonnettes.yml` — la planification (le « robot »)

---

## Installation (à faire une seule fois, ~10 min)

1. **Créez un compte GitHub** gratuit sur https://github.com (si vous n'en avez pas).

2. **Créez un dépôt** : bouton **New** → donnez-lui un nom
   (ex. `cartonnettes-nifty`) → laissez-le **Public** → **Create repository**.

3. **Déposez les fichiers** dans le dépôt, en respectant les dossiers :
   - Page du dépôt → **Add file** → **Upload files**.
   - Glissez `cartonnettes_a4.py` et `requirements.txt`.
   - Pour le workflow : le plus simple est **Add file** → **Create new file**,
     puis tapez comme nom de fichier exactement :
     `.github/workflows/cartonnettes.yml`
     et collez dedans le contenu du fichier fourni.
   - **Commit changes** pour valider.

4. **Donnez au robot le droit de publier** :
   onglet **Settings** → **Actions** → **General** →
   section *Workflow permissions* → cochez
   **Read and write permissions** → **Save**.

5. **Premier lancement (pour créer le lien)** :
   onglet **Actions** → workflow **Cartonnettes du mois** →
   bouton **Run workflow** → **Run workflow**.
   Au bout de 1-2 minutes, le PDF est généré et publié.

---

## Votre lien fixe

Une fois le premier lancement terminé, le PDF est **toujours** disponible ici
(remplacez `UTILISATEUR` et `DEPOT` par les vôtres) :

```
https://github.com/UTILISATEUR/DEPOT/releases/download/latest/Cartonnettes-A4-portrait.pdf
```

Exemple : si votre compte est `jdupont` et le dépôt `cartonnettes-nifty` :
`https://github.com/jdupont/cartonnettes-nifty/releases/download/latest/Cartonnettes-A4-portrait.pdf`

Ce lien ne change **jamais**. Chaque mois, le fichier derrière le lien est
remplacé par la version à jour. Mettez-le en favori, partagez-le, imprimez
directement depuis là.

---

## Bon à savoir

- **À la demande** : vous pouvez régénérer quand vous voulez sans attendre le
  1er du mois — onglet **Actions** → **Run workflow**.
- **Gratuit** : GitHub Actions est gratuit pour un dépôt public, largement dans
  les limites pour une exécution par mois.
- **Version paysage** : pour l'obtenir aussi, on peut ajouter quelques lignes au
  workflow (génération `--orientation paysage` publiée sous un second nom de
  fichier). Demandez si besoin.
- **Dépendance au site Nifty** : si Nifty modifie la structure de sa page
  `/offres/`, il faudra ajuster la fonction `decouvrir_urls()` du script.
