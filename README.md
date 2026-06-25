# SAE 2.01 – Application web Flask · Données de santé libérale

Application web Flask de visualisation des données de santé libérale et de prescriptions.
L’application utilise :
- une base de données MySQL locale pour les dimensions et les comptes utilisateurs,
- l’API `data.ameli.fr` pour les effectifs, les honoraires et les pathologies,
- l’API Odissé pour les données grippe.

## Équipe

- LIN ROMARIC
- MONAR NATHAN
- SIMON JAMAIN

## Prérequis

- Python 3.10 ou supérieur
- MySQL accessible contenant la base `SAE2.04` et les tables de dimensions
- Fichier `.env` avec les variables de configuration

## Installation

```bash
cd SAE201-App
pip install -r requirements.txt
```

Créer un fichier `.env` à partir d’un modèle et renseigner les variables suivantes :

- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_NAME`
- `SECRET_KEY`
- `APP_BASE_URL` (optionnel, utile en déploiement sous un sous-dossier)

## Lancement

```bash
python app.py
```

Puis ouvrir `http://localhost:5000` dans votre navigateur.

## Fonctionnalités

- Page d’accueil avec formulaire de recherche
- Cascade région → département côté client via API interne
- Consultation des effectifs par profession, département et année
- Courbe d’évolution des effectifs
- Pages dédiées aux honoraires et comparaisons départementales
- Page de suivi des professionnels et parcours métier
- Page de contact avec validation simple de formulaire
- Authentification : création de compte, connexion, espace privé
- Gestion des erreurs 404 et 500 avec page d’erreur personnalisée
- Routes API internes pour régions, départements, cache et pathologies

## Structure du projet

```
SAE201-App/
├── app.py                  ← point d'entrée Flask : enregistre les Blueprints et crée les tables manquantes
├── config.py               ← configuration (lecture du .env)
├── wsgi.py                 ← point d'entrée pour déploiement sur Alwaysdata
├── requirements.txt        ← dépendances Python
│
├── models/
│   ├── db.py               ← fabrique de sessions SQLAlchemy (engine + Session)
│   ├── dimensions.py       ← modèles ORM : Region, Departement, ProfessionSante, etc.
│   └── utilisateur.py      ← modèle ORM : table utilisateur (identifiant + mot de passe haché)
│
├── services/
│   ├── ameli_api.py        ← client HTTP paginé pour l'API data.ameli.fr (cache intégré)
│   ├── grippe_api.py       ← client HTTP paginé pour l'API Odissé (données grippales)
│   └── utilisateurs.py     ← logique métier : hachage SHA-256, création et authentification de compte
│
├── controllers/
│   ├── accueil.py          ← route / : page d'accueil avec formulaire de recherche
│   ├── effectifs.py        ← route /effectifs : tableau et graphique des effectifs par profession/région/année
│   ├── honoraires.py       ← route /honoraires : classement des départements et courbe de comparaison
│   ├── pathologies_api.py  ← route /pathologies : visualisation des pathologies par département
│   ├── dashboard.py        ← route /dashboard : vue synthétique multi-indicateurs
│   ├── contact.py          ← route /contact : formulaire de contact
│   ├── api.py              ← routes AJAX : cascade région → département
│   └── auth.py             ← routes /connexion, /creer-compte, /deconnexion, /espace
│
├── templates/
│   ├── base.html                ← template parent (navbar, footer, structure commune)
│   ├── accueil.html             ← page d'accueil
│   ├── effectifs.html           ← page effectifs
│   ├── honoraires.html          ← page honoraires (tableau + courbe Chart.js)
│   ├── pathologies.html         ← page pathologies
│   ├── prescription.html        ← page prescriptions
│   ├── professionnels.html      ← page professionnels de santé
│   ├── connexion.html           ← formulaire de connexion
│   ├── creer_compte.html        ← formulaire de création de compte
│   ├── espace.html              ← page privée : surveillance de la grippe (accès réservé)
│   ├── contact.html             ← formulaire de contact
│   ├── contact_confirmation.html← confirmation d'envoi du formulaire
│   └── erreur.html              ← page d'erreur générique (404, 500, erreurs métier)
│
└── static/
    ├── css/
    │   └── style.css            ← feuille de style principale
    └── js/
        ├── honoraires.js        ← logique de la page honoraires (onglets, pagination, Chart.js)
        ├── espace.js            ← logique de la page espace (courbe grippe Chart.js)
        ├── pathologies.js       ← logique de la page pathologies
        ├── prescription.js      ← logique de la page prescriptions
        ├── professionnels.js    ← logique de la page professionnels
        ├── cascade.js           ← cascade AJAX région → département (partagé)
        └── table_export.js      ← export de tableau (partagé)
```

## Dépendances principales

- `flask`
- `sqlalchemy`
- `pymysql`
- `python-dotenv`
- `requests`
- `cachetools`

## Notes

- `app.py` crée automatiquement la table `utilisateur` si elle n’existe pas.
- Certaines pages sont encore en développement et certaines routes API servent de base pour l’évolution future.
