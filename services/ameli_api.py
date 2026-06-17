import requests


class AmeliAPI:
    """Service d'accès à l'API data.ameli.fr.

    Centralise les URLs, la gestion des erreurs HTTP,
    et encapsule la mécanique des requêtes (principe POO).
    """

    BASE_URL = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets"

    _CORRESPONDANCES_HONORAIRES = {
        "Médecins généralistes (hors médecins à expertise particulière)":
            "Médecins généralistes (hors médecins à expertise particulière - MEP)",
        "Chirurgiens-dentistes spécialistes d'orthopédie dento-faciale":
            "Chirurgiens-dentistes spécialistes d'orthopédie dento-faciale (ODF)",
    }

    def __init__(self, timeout=10):
        self._timeout = timeout
        self._session = requests.Session()

    def get_effectifs(self, profession, departement_code, annee):
        """Effectifs pour une profession, un département et une année."""
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
        """Liste des pathologies disponibles dans l'API AMELI."""
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
        """Récupère et agrège les données des pathologies."""
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
            prev   = row.get("prev")
            pop    = row.get("npop")
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
                aggregates[key]["populations"]   += pop
            else:
                aggregates[key]["prev_weighted"] += prev * nombre
                aggregates[key]["populations"]   += nombre

        results = []
        for agg in aggregates.values():
            prevalence = 0.0
            if agg["populations"]:
                prevalence = 100.0 * agg["prev_weighted"] / agg["populations"]
            results.append({
                "annee":           agg["annee"],
                "region":          agg["region"],
                "departement":     agg["departement"],
                "pathologie":      agg["pathologie"],
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

    # Plafonds imposés par l'endpoint "records" de l'API Explore v2.1
    _PAGE_MAX   = 100     # nombre max de lignes par requête
    _OFFSET_MAX = 10000   # offset + limit doit rester <= 10000

    def _requete(self, dataset, params):
        """Méthode privée : effectue une requête GET (API Explore v2.1).

        L'API v2.1 pagine avec ``limit`` et ``offset`` (et NON ``rows``/``start``,
        qui appartiennent à l'ancienne API v1 : les envoyer provoque un 400).
        On récupère donc les données par pages de 100 au maximum.
        """
        url    = f"{self.BASE_URL}/{dataset}/records"
        params = params.copy()

        # Nombre total de lignes souhaité (None = pas de limite explicite)
        total_voulu = None
        for cle in ("limit", "rows"):          # "rows" toléré par compat. ascendante
            if cle in params:
                try:
                    total_voulu = int(params.pop(cle))
                except (TypeError, ValueError):
                    total_voulu = None
                break
        params.pop("start", None)               # jamais envoyé à l'API v2.1

        all_results = []
        offset = 0
        while True:
            # Taille de la page courante (respecte le total voulu et le plafond)
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
                # On remonte le corps de la réponse de l'API : c'est lui qui
                # indique la vraie cause d'un 400 (champ inconnu, ODSQL invalide…).
                detail = ""
                reponse = getattr(e, "response", None)
                if reponse is not None:
                    detail = f" | réponse API : {reponse.text[:300]}"
                print(f"[AmeliAPI] Erreur : {e}{detail}")
                return all_results

            all_results.extend(page_results)

            # Arrêts : page incomplète (= dernière), total atteint, ou plafond offset
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

    # ── Méthodes honoraires ───────────────────────────────────────────────

    def get_honoraires(self, profession, departement_code, annee):
        """Honoraires détaillés pour une profession, un département et une année.

        group_by supprimé : l'API refuse year() + group_by combinés (erreur 400).
        Les filtres where suffisent à éviter les doublons sur ce dataset.
        """
        profession = self._CORRESPONDANCES_HONORAIRES.get(profession, profession)
        where = (
            f'profession_sante="{profession}" AND '
            f'departement="{departement_code}" AND '
            f'year(annee)={annee} AND '
            f'vision_profession_territoire="oui" AND '
            f'montant_honoraires IS NOT NULL'
        )
        return self._requete(
            "honoraires-detailles",
            {
                "select": (
                    "year(annee) as annee,"
                    "type_honoraires_niveau_1,"
                    "type_honoraires_niveau_2,"
                    "type_honoraires_niveau_3,"
                    "montant_honoraires,"
                    "montant_honoraires_moyens"
                ),
                "where": where,
                "order_by": (
                    "honoraires_ordre_niv_1,"
                    "honoraires_ordre_niv_2,"
                    "honoraires_ordre_niv_3"
                ),
                "limit": 100,
            },
        )

    def get_evolution_honoraires(self, profession, departement_code):
        """Évolution du montant total des honoraires sur toutes les années.

        group_by supprimé : même raison que get_honoraires().
        """
        profession = self._CORRESPONDANCES_HONORAIRES.get(profession, profession)
        where = (
            f'profession_sante="{profession}" AND '
            f'departement="{departement_code}" AND '
            f'type_honoraires_niveau_1="Ensemble des honoraires" AND '
            f'type_honoraires_niveau_2 IS NULL AND '
            f'vision_profession_territoire="oui" AND '
            f'montant_honoraires_moyens IS NOT NULL'
        )
        return self._requete(
            "honoraires-detailles",
            {
                "select": (
                    "year(annee) as annee,"
                    "montant_honoraires,"
                    "montant_honoraires_moyens"
                ),
                "where": where,
                "order_by": "annee",
                "limit": 100,
            },
        )

    def get_evolution_comparaison(self, profession, departement_1, departement_2, type_honoraires_niv1):
        """Comparaison de l'évolution entre deux départements.

        group_by supprimé : même raison que get_honoraires().
        """
        profession = self._CORRESPONDANCES_HONORAIRES.get(profession, profession)
        where = (
            f'profession_sante="{profession}" AND '
            f'(departement="{departement_1}" OR departement="{departement_2}") AND '
            f'type_honoraires_niveau_1="{type_honoraires_niv1}" AND '
            f'type_honoraires_niveau_2 IS NULL AND '
            f'vision_profession_territoire="oui" AND '
            f'montant_honoraires_moyens IS NOT NULL'
        )
        return self._requete(
            "honoraires-detailles",
            {
                "select": (
                    "year(annee) as annee,"
                    "departement,"
                    "libelle_departement,"
                    "montant_honoraires_moyens"
                ),
                "where": where,
                "order_by": "annee,departement",
                "limit": 200,
            },
        )

    def get_classement_departements(self, profession, annee):
        """Classement des départements par montant moyen.

        group_by conservé ici car pas de year() dans le select — pas de conflit.
        """
        profession = self._CORRESPONDANCES_HONORAIRES.get(profession, profession)
        where = (
            f'profession_sante="{profession}" AND '
            f'year(annee)={annee} AND '
            f'type_honoraires_niveau_1="Ensemble des honoraires" AND '
            f'type_honoraires_niveau_2 IS NULL AND '
            f'vision_profession_territoire="oui" AND '
            f'montant_honoraires_moyens IS NOT NULL'
        )
        resultats = self._requete(
            "honoraires-detailles",
            {
                "select": (
                    "departement,"
                    "libelle_departement,"
                    "montant_honoraires_moyens"
                ),
                "where": where,
                "group_by": (
                    "departement,"
                    "libelle_departement,"
                    "montant_honoraires_moyens"
                ),
                "limit": 200,
            },
        )
        def cle_tri(r):
            try:
                return float(r.get("montant_honoraires_moyens") or 0)
            except (TypeError, ValueError):
                return 0.0
        return sorted(resultats, key=cle_tri, reverse=True)