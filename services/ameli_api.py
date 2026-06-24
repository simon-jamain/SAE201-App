import logging
import hashlib
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from cachetools import TTLCache
from threading import Lock

logger = logging.getLogger(__name__)

# ── Cache en mémoire ──────────────────────────────────────────────────────────
# TTL : 24 h (les données ameli.fr sont publiées annuellement)
# maxsize : 512 entrées — amplement suffisant pour toutes les combinaisons
#           profession × territoire × année × dataset
_cache: TTLCache = TTLCache(maxsize=512, ttl=86400)
_cache_lock = Lock()


def _cache_key(dataset: str, params: dict) -> str:
    """Clé de cache déterministe à partir du dataset et des paramètres."""
    raw = json.dumps({"dataset": dataset, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


class AmeliAPI:
    """Service d'accès à l'API data.ameli.fr — datasets vérifiés."""

    BASE_URL = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets"

    # Correspondances de libellés pour le dataset honoraires (certaines
    # professions y sont nommées différemment des autres datasets).
    _CORRESPONDANCES_HONORAIRES = {
        "Médecins généralistes (hors médecins à expertise particulière)":
            "Médecins généralistes (hors médecins à expertise particulière - MEP)",
        "Chirurgiens-dentistes spécialistes d'orthopédie dento-faciale":
            "Chirurgiens-dentistes spécialistes d'orthopédie dento-faciale (ODF)",
    }

    # Plafonds imposés par l'endpoint "records" de l'API Explore v2.1
    _PAGE_MAX   = 100     # nombre max de lignes par requête
    _OFFSET_MAX = 10000   # offset + limit doit rester <= 10000

    def __init__(self, timeout=30):
        self._timeout = timeout
        self._session = requests.Session()

        # Retry automatique : 3 tentatives, délai exponentiel (1s, 2s, 4s)
        # Déclenché sur erreurs réseau ET codes HTTP 429/500/502/503/504
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://",  adapter)

    # ── Effectifs totaux ───────────────────────────────────────────────────

    def get_effectifs(self, profession, departement_code, annee):
        where = (
            f'profession_sante="{profession}" AND '
            f'departement="{departement_code}" AND '
            f"year(annee)={annee} AND "
            f'libelle_classe_age="Tout âge" AND '
            f'libelle_sexe="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {"select": "annee,effectif,densite", "where": where, "limit": 100},
        )

    def get_evolution_effectifs(self, profession, departement_code, region_code=None):
        """Effectifs sur toutes les années. Si departement_code=None, filtre par région."""
        if departement_code:
            territoire = f'departement="{departement_code}"'
        else:
            territoire = f'region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire} AND '
            f'libelle_classe_age="Tout âge" AND '
            f'libelle_sexe="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {"select": "annee,effectif,densite", "where": where,
             "order_by": "annee", "limit": 100},
        )

    # ── Effectifs par SEXE ─────────────────────────────────────────────────

    def get_effectifs_par_sexe(self, profession, departement_code, annee, region_code=None):
        if departement_code:
            territoire = f'departement="{departement_code}"'
        else:
            territoire = f'region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire} AND '
            f"year(annee)={annee} AND "
            f'libelle_classe_age="Tout âge" AND '
            f'libelle_sexe!="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {"select": "libelle_sexe,effectif", "where": where, "limit": 10},
        )

    # ── Effectifs par TRANCHE D'ÂGE ───────────────────────────────────────

    def get_effectifs_par_age(self, profession, departement_code, annee, region_code=None):
        if departement_code:
            territoire = f'departement="{departement_code}"'
        else:
            territoire = f'region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire} AND '
            f"year(annee)={annee} AND "
            f'libelle_classe_age!="Tout âge" AND '
            f'libelle_sexe="tout sexe"'
        )
        return self._requete(
            "demographie-effectifs-et-les-densites",
            {"select": "libelle_classe_age,effectif",
             "where": where, "order_by": "libelle_classe_age", "limit": 20},
        )

    # ── Exercices libéraux ─────────────────────────────────────────────────
    # Champ territoire : "code_departement" (pas "departement")

    def get_exercices(self, profession, departement_code, annee, region_code=None):
        if departement_code:
            territoire = f'code_departement="{departement_code}"'
        else:
            territoire = f'region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire} AND '
            f"year(annee)={annee}"
        )
        return self._requete(
            "demographie-exercices-liberaux",
            {"select": "annee,libelle_type_exercice_liberal,effectif",
             "where": where, "limit": 20},
        )

    def get_evolution_exercices(self, profession, departement_code, region_code=None):
        if departement_code:
            territoire = f'code_departement="{departement_code}"'
        else:
            territoire = f'region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire}'
        )
        return self._requete(
            "demographie-exercices-liberaux",
            {"select": "annee,libelle_type_exercice_liberal,effectif",
             "where": where, "order_by": "annee", "limit": 200},
        )

    # ── Pathologies ────────────────────────────────────────────────────────

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
        ) or []
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
        ) or []

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

    # ── Honoraires ─────────────────────────────────────────────────────────

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
        ) or []
        def cle_tri(r):
            try:
                return float(r.get("montant_honoraires_moyens") or 0)
            except (TypeError, ValueError):
                return 0.0
        return sorted(resultats, key=cle_tri, reverse=True)

    # ── Médicaments & Actes (Open Medic / Open Damir) ──────────────────────

    def get_medicaments(self, annee, poste_id=None, limit=50):
        # On interroge le catalogue global pour voir les vrais IDs disponibles
        url_catalogue = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets?where=prescriptions&limit=10"
        try:
            reponse = self._session.get(url_catalogue, timeout=self._timeout)
            if reponse.status_code == 200:
                datasets = reponse.json().get('datasets', [])
                print("\n═════════════ DATASETS TROUVÉS SUR AMELI ═════════════")
                for d in datasets:
                    print(f"ID ÉCRIT POUR LE CODE -> : {d.get('dataset_id')}")
                    print(f"Titre affiché sur le site : {d.get('metas', {}).get('default', {}).get('title')}\n")
                print("══════════════════════════════════════════════════════\n")
        except Exception as e:
            print(f"Erreur lors du scan du catalogue : {e}")

        # En attendant que tu lises le terminal, on renvoie une liste vide
        # pour éviter l'erreur 503 et laisser ton formulaire s'afficher !
        return []

    # ── Méthode privée : requête HTTP avec pagination + cache + retry ──────

    def _requete(self, dataset, params):
        """Exécute un appel GET vers l'API ameli.fr (API Explore v2.1).

        Combine trois mécaniques :
          • Pagination ``limit``/``offset`` par pages de 100 (l'API v2.1 refuse
            ``rows``/``start`` de l'ancienne v1 : les envoyer provoque un 400).
          • Cache TTL 24 h (les données ameli.fr sont publiées annuellement).
          • Retry automatique (configuré sur la session dans __init__).

        Retourne la liste des enregistrements en cas de succès, ou ``None`` en
        cas d'échec réseau / HTTP. Le ``None`` permet aux contrôleurs de
        distinguer « API en panne » (page d'erreur 503) de « aucun résultat »
        (liste vide).
        """
        # Le cache porte sur la requête logique complète (avant pagination).
        key = _cache_key(dataset, params)
        with _cache_lock:
            cached = _cache.get(key)
        if cached is not None:
            logger.debug("[AmeliAPI] Cache HIT  — %s", dataset)
            return cached

        logger.debug("[AmeliAPI] Cache MISS — %s", dataset)

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
                logger.error("[AmeliAPI] Erreur sur %s : %s%s", dataset, e, detail)
                # Échec : on renvoie None (et on ne met rien en cache).
                return None

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
            all_results = all_results[:total_voulu]

        # Succès : mise en cache de la réponse complète.
        with _cache_lock:
            _cache[key] = all_results

        return all_results

    # ── Utilitaires de cache (optionnel) ───────────────────────────────────

    @staticmethod
    def cache_info() -> dict:
        """Retourne des statistiques sur le cache (pour debug/admin)."""
        return {
            "taille_actuelle": len(_cache),
            "taille_max":      _cache.maxsize,
            "ttl_secondes":    _cache.ttl,
        }

    @staticmethod
    def vider_cache() -> None:
        """Vide entièrement le cache (à utiliser avec parcimonie)."""
        with _cache_lock:
            _cache.clear()
        logger.info("[AmeliAPI] Cache vidé manuellement.")