# services/grippe_api.py
import requests


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

    BASE_URL = "https://odisse.santepubliquefrance.fr/api/explore/v2.1/catalog/datasets"
    DATASET  = "grippe-passages-aux-urgences-et-actes-sos-medecins-departement"

    _PAGE_MAX   = 100
    _OFFSET_MAX = 10000

    CLASSES_AGE = ["Tous âges", "00-04 ans", "05-14 ans", "15-64 ans", "65 ans ou plus"]

    def __init__(self, timeout=10):
        self._timeout = timeout
        self._session = requests.Session()

    def _requete(self, params):
        """Méthode privée : requête GET paginée (limit/offset, API v2.1)."""
        url    = f"{self.BASE_URL}/{self.DATASET}/records"
        params = params.copy()

        total_voulu = None
        if "limit" in params:
            try:
                total_voulu = int(params.pop("limit"))
            except (TypeError, ValueError):
                total_voulu = None

        all_results = []
        offset = 0
        while True:
            page = self._PAGE_MAX
            if total_voulu is not None:
                page = min(page, total_voulu - len(all_results))
            if page <= 0:
                break

            params["limit"]  = page
            params["offset"] = offset

            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                resp.raise_for_status()
                page_results = resp.json().get("results", [])
            except requests.RequestException as e:
                detail = ""
                reponse = getattr(e, "response", None)
                if reponse is not None:
                    detail = f" | réponse API : {reponse.text[:300]}"
                print(f"[GrippeAPI] Erreur : {e}{detail}")
                return all_results

            all_results.extend(page_results)

            if len(page_results) < page:
                break
            if total_voulu is not None and len(all_results) >= total_voulu:
                break
            offset += page
            if offset >= self._OFFSET_MAX:
                break

        if total_voulu is not None:
            return all_results[:total_voulu]
        return all_results

    # ── Évolution dans le temps pour un département (tout l'historique) ─────
    def get_evolution_departement(self, dep_code, classe_age):
        """Toutes les semaines disponibles (~6 saisons, 2020 à aujourd'hui)
        pour un département et une classe d'âge donnés, triées
        chronologiquement. C'est la seule vue proposée : elle fait
        apparaître les vagues épidémiques hivernales par contraste avec
        le reste de l'année, contrairement à un classement instantané qui
        est dominé par le bruit statistique en période hors épidémie.
        """
        where = f'dep="{dep_code}" AND sursaud_cl_age_gene="{classe_age}"'
        return self._requete({
            "select": (
                "date_complet,semaine,libgeo,"
                "taux_passages_grippe_sau,taux_hospit_grippe_sau"
            ),
            "where": where,
            "order_by": "date_complet",
            "limit": 400,  # ~330 semaines disponibles, marge incluse
        })