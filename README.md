# SAE 2.01 – Application web Flask · Données de santé libérale

Application web Flask qui interroge la base SAE2.04 et l'API data.ameli.fr pour visualiser les effectifs et densités des professionnels de santé libéraux.

## Équipe

<!-- Remplacer par les membres de l'équipe -->
- Prénom Nom
- Prénom Nom

## Prérequis

- Python 3.10 ou supérieur
- Base MySQL SAE2.04 accessible (tables de dimensions remplies)

## Installation

```bash
# 1. Cloner / décompresser le projet
cd SAE201_ROMA

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer le fichier .env à partir du modèle
cp .env.example .env
# → Remplir DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, SECRET_KEY
```

## Lancement

```bash
python app.py
```

Ouvrir ensuite http://localhost:5000 dans un navigateur.

## Fonctionnalités implémentées

### Minimales
- [x] Page d'accueil avec formulaire (profession, région, département, année)
- [x] Cascade région → département en AJAX
- [x] Page de résultats : tableau effectifs/densités
- [x] Graphique d'évolution (Chart.js)
- [x] Gestion d'erreur 404 et message explicite si l'API ne répond pas
- [x] Page de contact

### Avancées
<!-- Cocher ce qui a été réalisé -->
- [ ] Page Honoraires
- [ ] Page Prescriptions
- [ ] Comparaison entre deux départements
- [ ] Mise en cache des appels API
- [ ] Export CSV

## Structure du projet

```
SAE201_ROMA/
├── app.py            ← point d'entrée Flask
├── config.py         ← configuration
├── wsgi.py           ← déploiement Alwaysdata
├── requirements.txt
├── models/           ← classes ORM (Region, Departement, ProfessionSante)
├── services/         ← AmeliAPI
├── controllers/      ← routes Flask (accueil, effectifs, api, contact)
├── templates/        ← HTML Jinja2
└── static/           ← CSS, JS
```
