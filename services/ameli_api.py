import requests


class AmeliAPI:
    """Service d'accès à l'API data.ameli.fr.

    Centralise les URLs, la gestion des erreurs HTTP,
    et encapsule la mécanique des requêtes (principe POO).
    """

    BASE_URL = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets"

    def __init__(self, timeout=10):
        # Attributs privés (convention _ : ne pas utiliser depuis l'extérieur)
        self._timeout = timeout
        self._session = requests.Session()

    def get_effectifs(self, profession, departement_code, annee):
        """Effectifs pour une profession, un département et une année.

        Retourne une liste de dictionnaires {annee, effectif, densite}.
        """
        where = (
            f'profession_sante="{profession}" AND '
            f'departement="{departement_code}" AND '
            f'year(annee)={annee} AND '
            f'libelle_classe_age="Tout âge" AND '
            f'libelle_sexe="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {"select": "annee,effectif,densite", "where": where, "limit": 100},
        )

    def get_evolution_effectifs(self, profession, departement_code):
        """Effectifs sur toutes les années disponibles (pour le graphique)."""
        where = (
            f'profession_sante="{profession}" AND '
            f'departement="{departement_code}" AND '
            f'libelle_classe_age="Tout âge" AND '
            f'libelle_sexe="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {
                "select": "annee,effectif,densite",
                "where": where,
                "order_by": "annee",
                "limit": 100,
            },
        )

    def get_pathology_labels(self, annee=None):
        """Liste des pathologies disponibles dans l'API AMELI (dataset effectifs)."""
        clauses = [
            'cla_age_5="tsage"',
            'sexe="9"',
            'niveau_prioritaire="1"',
            'dept!="999"',
        ]
        if annee:
            clauses.append(f"year(annee)={annee}")

        results = self._requete(
            "effectifs",
            {
                "select": "patho_niv1",
                "group_by": "patho_niv1",
                "where": " AND ".join(clauses),
                "limit": 500,
            },
        )
        labels = sorted({r.get("patho_niv1") for r in results if r.get("patho_niv1")})
        return labels

    def get_pathologies(self, annee=None, pathologie="all", region=None, departement=None, limit=5000):
        """Récupère et agrège les données des pathologies depuis l'API AMELI (dataset effectifs)."""
        clauses = [
            'cla_age_5="tsage"',
            'sexe="9"',
            'niveau_prioritaire="1"',
            'dept!="999"',
        ]
        if annee:
            clauses.append(f"year(annee)={annee}")
        if pathologie and pathologie != "all":
            safe_patho = pathologie.replace('"', '\\"')
            clauses.append(f'patho_niv1="{safe_patho}"')
        if region:
            clauses.append(f'region="{region}"')
        if departement:
            clauses.append(f'dept="{departement}"')

        raw = self._requete(
            "effectifs",
            {
                "select": "annee,region,dept,patho_niv1,ntop,npop,prev",
                "where": " AND ".join(clauses),
                "limit": limit,
            },
        )

        aggregates = {}
        for row in raw:
            key = (
                row.get("annee"),
                row.get("region"),
                row.get("dept"),
                row.get("patho_niv1"),
            )
            if key not in aggregates:
                aggregates[key] = {
                    "annee": row.get("annee"),
                    "region": row.get("region"),
                    "departement": row.get("dept"),
                    "pathologie": row.get("patho_niv1"),
                    "nombre_patients": 0.0,
                    "populations": 0.0,
                    "prev_weighted": 0.0,
                }

            nombre = row.get("ntop")
            prev = row.get("prev")
            pop = row.get("npop")
            try:
                nombre = float(nombre)
            except (TypeError, ValueError):
                nombre = 0.0
            try:
                pop = float(pop) if pop is not None else 0.0
            except (TypeError, ValueError):
                pop = 0.0
            try:
                prev = float(prev) if prev is not None else 0.0
            except (TypeError, ValueError):
                prev = 0.0

            aggregates[key]["nombre_patients"] += nombre
            if pop > 0:
                aggregates[key]["prev_weighted"] += prev * pop
                aggregates[key]["populations"] += pop
            else:
                aggregates[key]["prev_weighted"] += prev * nombre
                aggregates[key]["populations"] += nombre

        results = []
        for agg in aggregates.values():
            prevalence = 0.0
            if agg["populations"]:
                prevalence = 100.0 * agg["prev_weighted"] / agg["populations"]
            results.append({
                "annee": agg["annee"],
                "region": agg["region"],
                "departement": agg["departement"],
                "pathologie": agg["pathologie"],
                "nombre_patients": agg["nombre_patients"],
                "taux_prevalence": round(prevalence, 2),
            })

        return sorted(
            results,
            key=lambda item: (
                item["region"],
                item["departement"],
                item["pathologie"] or "",
            ),
        )

    def _requete(self, dataset, params):
        """Méthode privée : effectue une requête GET et gère les erreurs."""
        url = f"{self.BASE_URL}/{dataset}/records"
        params = params.copy()
        limit = None
        if "limit" in params:
            try:
                limit = int(params.pop("limit"))
            except (TypeError, ValueError):
                limit = None

        rows = None
        if "rows" in params:
            try:
                rows = int(params["rows"])
            except (TypeError, ValueError):
                rows = None

        if limit is not None and limit > 0:
            rows = min(limit, 100)
        elif rows is not None and rows > 100:
            rows = 100

        if rows is not None:
            params["rows"] = rows

        if limit is None:
            limit = rows

        all_results = []
        start = 0
        while True:
            if start:
                params["start"] = start
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                resp.raise_for_status()
                page_results = resp.json().get("results", [])
            except requests.RequestException as e:
                print(f"[AmeliAPI] Erreur : {e}")
                return all_results

            all_results.extend(page_results)
            if not page_results or rows is None:
                break
            if limit is not None and len(all_results) >= limit:
                break
            if len(page_results) < rows:
                break
            start += rows
            if limit is not None and start >= limit:
                break

        if limit is not None:
            return all_results[:limit]
        return all_results
