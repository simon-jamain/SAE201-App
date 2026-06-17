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
            territoire = f'code_region="{region_code}"'
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
            territoire = f'code_region="{region_code}"'
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
            territoire = f'code_region="{region_code}"'
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
            territoire = f'code_region="{region_code}"'
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
            territoire = f'code_region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire}'
        )
        return self._requete(
            "demographie-exercices-liberaux",
            {"select": "annee,libelle_type_exercice_liberal,effectif",
             "where": where, "order_by": "annee", "limit": 200},
        )

    # ── Secteurs conventionnels ────────────────────────────────────────────
    # Champ territoire : "code_departement"

    def get_secteurs(self, profession, departement_code, annee, region_code=None,
                     secteur_libelle=None):
        """
        Récupère les secteurs conventionnels.
        secteur_libelle : filtre optionnel, ex. "Secteur 1", "Secteur 2", "Non conventionné"
        """
        if departement_code:
            territoire = f'code_departement="{departement_code}"'
        else:
            territoire = f'code_region="{region_code}"'
        where = (
            f'profession_sante="{profession}" AND '
            f'{territoire} AND '
            f"year(annee)={annee}"
        )
        if secteur_libelle:
            where += f' AND libelle_secteur_conventionnel="{secteur_libelle}"'
        return self._requete(
            "demographie-secteurs-conventionnels",
            {"select": "annee,libelle_secteur_conventionnel,effectif",
             "where": where, "limit": 20},
        )


# ── Méthode privée ─────────────────────────────────────────────────────

    def _requete(self, dataset, params):
        """
        Exécute un appel GET vers l'API ameli.fr avec mise en cache TTL 24 h.
        Utilise l'architecture moderne v2.1 standard d'OpenDataSoft.
        """
        key = _cache_key(dataset, params)

        with _cache_lock:
            cached = _cache.get(key)

        if cached is not None:
            logger.debug("[AmeliAPI] Cache HIT  — %s", dataset)
            return cached

        logger.debug("[AmeliAPI] Cache MISS — %s", dataset)

        # URL officielle et unique v2.1 pour TOUS les datasets (sans distinction)
        url = f"{self.BASE_URL}/{dataset}/records"

        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            
            # En v2.1, les résultats sont TOUJOURS dans la clé "results"
            data = resp.json().get("results", [])

        except requests.exceptions.Timeout:
            logger.error("[AmeliAPI] Timeout sur %s (>%ds)", dataset, self._timeout)
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error("[AmeliAPI] Connexion impossible sur %s : %s", dataset, e)
            return None
        except requests.exceptions.HTTPError as e:
            logger.error("[AmeliAPI] HTTP %s sur %s : %s",
                         e.response.status_code if e.response else "?", dataset, e)
            return None
        except requests.RequestException as e:
            logger.error("[AmeliAPI] Erreur sur %s : %s: %s", dataset, type(e).__name__, e)
            return None

        if data is not None:
            with _cache_lock:
                _cache[key] = data

        return data
    # ── Médicaments & Actes (Open Medic / Open Damir) ──────────────────────
    def get_medicaments(self, annee, poste_id=None, limit=50):
            import requests
            
            # On interroge le catalogue global pour voir les vrais IDs disponibles
            url_catalogue = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets?where=prescriptions&limit=10"
            try:
                reponse = requests.get(url_catalogue)
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
