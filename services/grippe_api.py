# services/grippe_api.py
import requests  # bibliothèque HTTP tierce permettant d'envoyer des requêtes GET vers l'API Odissé et de gérer les erreurs réseau


class GrippeAPI:
    """Service d'accès à l'API Odissé (Santé publique France) — dataset
    grippe par département. Même esprit que AmeliAPI : centralise l'URL,
    la requête HTTP (pagination limit/offset) et la gestion des erreurs.

    Le dataset couvre ~6 saisons (2020-S01 à aujourd'hui), par département
    et classe d'âge. Un classement instantané sur la dernière semaine n'est
    pas fiable hors période épidémique (taux très bruités en été, faute de
    volume) : on se limite donc à l'évolution dans le temps, qui fait
    apparaître clairement les vagues hivernales par contraste avec le reste
    de l'année.
    """

    BASE_URL = "https://odisse.santepubliquefrance.fr/api/explore/v2.1/catalog/datasets"  # URL racine de l'API Odissé de Santé Publique France
    DATASET  = "grippe-passages-aux-urgences-et-actes-sos-medecins-departement"           # identifiant du dataset grippe utilisé pour construire l'URL d'accès aux enregistrements

    _PAGE_MAX   = 100    # nombre maximum d'enregistrements récupérés par page, imposé par l'API Explore v2.1
    _OFFSET_MAX = 10000  # offset maximum autorisé par l'API, au-delà duquel la pagination s'arrête pour ne pas boucler indéfiniment

    CLASSES_AGE = ["Tous âges", "00-04 ans", "05-14 ans", "15-64 ans", "65 ans ou plus"]  # tranches d'âge disponibles dans le dataset, utilisées pour valider et remplir le select de la page espace.html

    def __init__(self, timeout=10):
        self._timeout = timeout          # durée maximale d'attente en secondes pour chaque requête HTTP (évite de bloquer la page si l'API est lente)
        self._session = requests.Session()  # instance requests partagée entre toutes les requêtes de l'objet (réutilise la connexion TCP, évite de la rouvrir à chaque appel)

    def _requete(self, params):
        """Méthode privée : requête GET paginée (limit/offset, API v2.1)."""
        url    = f"{self.BASE_URL}/{self.DATASET}/records"  # construit l'URL complète d'accès aux enregistrements du dataset
        params = params.copy()  # copie le dictionnaire pour ne pas modifier le dictionnaire original passé en paramètre

        total_voulu = None
        if "limit" in params:
            try:
                total_voulu = int(params.pop("limit"))  # extrait et convertit le nombre total d'enregistrements souhaité (retiré de params car géré manuellement via la pagination)
            except (TypeError, ValueError):
                total_voulu = None  # si la valeur est invalide, on n'impose pas de limite

        all_results = []  # liste qui accumule les enregistrements au fil des pages
        offset = 0        # nombre d'enregistrements à sauter avant de commencer à renvoyer des résultats (incrémenté à chaque page)
        while True:
            page = self._PAGE_MAX
            if total_voulu is not None:
                page = min(page, total_voulu - len(all_results))  # réduit la taille de la dernière page pour ne pas dépasser le total voulu
            if page <= 0:
                break  # le nombre total d'enregistrements demandé est atteint, on arrête la pagination

            params["limit"]  = page    # taille de la page courante envoyée à l'API
            params["offset"] = offset  # position de départ dans le dataset pour cette page

            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)  # envoie la requête GET à l'API avec les paramètres de pagination
                resp.raise_for_status()                                               # lève une exception si le code HTTP est une erreur (4xx ou 5xx)
                page_results = resp.json().get("results", [])                        # extrait la liste des enregistrements du champ "results" de la réponse JSON (liste vide si le champ est absent)
            except requests.RequestException as e:
                detail = ""
                reponse = getattr(e, "response", None)
                if reponse is not None:
                    detail = f" | réponse API : {reponse.text[:300]}"  # extrait les 300 premiers caractères du corps de la réponse pour identifier la cause de l'erreur (champ inconnu, filtre invalide, etc.)
                print(f"[GrippeAPI] Erreur : {e}{detail}")
                return all_results  # en cas d'erreur réseau ou HTTP, retourne les résultats déjà accumulés plutôt que de propager l'exception (évite de faire planter la page)

            all_results.extend(page_results)  # ajoute les enregistrements de la page courante à la liste globale

            if len(page_results) < page:
                break  # page incomplète : l'API n'a plus de données à renvoyer, on arrête la pagination
            if total_voulu is not None and len(all_results) >= total_voulu:
                break  # le nombre total d'enregistrements demandé est atteint
            offset += page           # décale l'offset pour récupérer la page suivante
            if offset >= self._OFFSET_MAX:
                break  # offset maximum atteint : on s'arrête pour respecter la limite de l'API

        if total_voulu is not None:
            return all_results[:total_voulu]  # tronque au nombre exact demandé (la dernière page peut avoir renvoyé plus que nécessaire)
        return all_results  # retourne tous les enregistrements accumulés


    # ── Évolution dans le temps pour un département (tout l'historique) ─────
    def get_evolution_departement(self, dep_code, classe_age):
        """Toutes les semaines disponibles (~6 saisons, 2020 à aujourd'hui)
        pour un département et une classe d'âge donnés, triées
        chronologiquement. C'est la seule vue proposée : elle fait
        apparaître les vagues épidémiques hivernales par contraste avec
        le reste de l'année, contrairement à un classement instantané qui
        est dominé par le bruit statistique en période hors épidémie.
        """
        where = f'dep="{dep_code}" AND sursaud_cl_age_gene="{classe_age}"'  # filtre ODSQL combinant le code département et la classe d'âge sélectionnés par l'utilisateur
        return self._requete({
            "select": (
                "date_complet,semaine,libgeo,"
                "taux_passages_grippe_sau,taux_hospit_grippe_sau"  # colonnes utiles : date, semaine, nom du département, taux de passages aux urgences et taux d'hospitalisations pour grippe
            ),
            "where": where,
            "order_by": "date_complet",  # tri chronologique pour que la courbe s'affiche dans le bon sens
            "limit": 400,  # ~330 semaines disponibles, marge incluse
        })