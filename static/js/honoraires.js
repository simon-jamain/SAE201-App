/* honoraires.js — logique de la page Honoraires
   (onglets, choix de visualisation, cascade région→département,
    pagination du classement, graphique courbe).
   Les données du serveur sont lues depuis les îlots <script type="application/json">. */

(function () {
  "use strict";

  // ── Lecture d'un îlot de données JSON injecté par le serveur ─────────────
  function lireJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      console.error("JSON invalide dans #" + id, e);
      return null;
    }
  }

  const config   = lireJSON("page-config") || {};
  const BASE_URL = config.baseUrl || "";
  const VIZ_TYPE = config.vizType || "tableau";

  // Indications affichées selon la visualisation choisie
  const VIZ_HINTS = {
    tableau: "Requiert une profession et une année.",
    courbe:  "Requiert une profession, une année et DEUX départements à comparer.",
  };

  // ── Onglets (Type de visualisation / Filtres) ───────────────────────────
  function switchTab(btn, tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    const tab = document.getElementById(tabId);
    if (tab) tab.classList.add("active");
  }

  // ── Affichage des filtres selon la visualisation ────────────────────────
  // Région, Département et les champs de comparaison ne servent qu'à la courbe.
  function majFiltresComparaison(type) {
    const afficher = (type === "courbe");
    document.querySelectorAll(".group-comparaison").forEach(g => {
      g.style.display = afficher ? "" : "none";
    });
  }

  function majIndication(type) {
    const hint = document.getElementById("viz-hint");
    if (hint) hint.textContent = VIZ_HINTS[type] || "";
  }

  // ── Choix de la visualisation ───────────────────────────────────────────
  function setViz(btn, type) {
    const input = document.getElementById("viz_type_input");
    if (input) input.value = type;

    document.querySelectorAll("[data-viz]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    majFiltresComparaison(type);
    majIndication(type);

    // Si profession + année sont déjà choisies, on relance la requête pour
    // obtenir la bonne visualisation (un seul aller-retour serveur).
    const prof  = document.getElementById("profession");
    const annee = document.getElementById("annee");
    const form  = document.getElementById("form-filters");
    if (form && prof && annee && prof.value && annee.value) {
      form.submit();
    }
  }

  // ── Cascade région → département (générique : une fonction, deux usages) ──
  function brancherCascade(idRegion, idDept) {
    const selRegion = document.getElementById(idRegion);
    const selDept   = document.getElementById(idDept);
    if (!selRegion || !selDept) return;

    selRegion.addEventListener("change", async (e) => {
      const regionId = e.target.value;
      selDept.innerHTML = '<option value="">-- Choisir --</option>';
      if (!regionId) return;
      try {
        const resp  = await fetch(`${BASE_URL}/api/departements/${regionId}`);
        const depts = await resp.json();
        depts.forEach(d => {
          const opt = document.createElement("option");
          opt.value = d.code;
          opt.textContent = `${d.code} – ${d.libelle}`;
          selDept.appendChild(opt);
        });
      } catch (err) {
        console.error("Cascade départements :", err);
      }
    });
  }

  // ── Tableau du classement : pagination (10 lignes par page) ─────────────
  function initClassement() {
    const rows = lireJSON("data-classement");
    if (!rows) return;

    const tbody = document.getElementById("tbody-classement");
    const nav   = document.getElementById("pagination-classement");
    if (!tbody || !nav) return;

    const perPage    = 10;
    const totalPages = Math.ceil(rows.length / perPage);

    function renderPage(p) {
      const start = (p - 1) * perPage;
      const slice = rows.slice(start, start + perPage);

      tbody.innerHTML = slice.map((r, i) => `
        <tr>
          <td>${start + i + 1}</td>
          <td>${r.libelle_departement || r.departement}</td>
          <td class="num">${r.montant_honoraires_moyens}</td>
        </tr>
      `).join("");

      nav.innerHTML = "";
      for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = i;
        btn.className = "viz-btn" + (i === p ? " active" : "");
        btn.onclick = () => renderPage(i);
        nav.appendChild(btn);
      }
    }

    renderPage(1);
  }

  // ── Graphique courbe (comparaison de deux départements) ─────────────────
  function initCourbe() {
    const cfg = lireJSON("data-courbe");
    if (!cfg || !cfg.series) return;

    const canvas = document.getElementById("courbe-canvas");
    if (!canvas || typeof Chart === "undefined") return;

    const colors = ["#2E74B5", "#E05A2B", "#2E9E6B", "#F0B429"];
    const datasets = cfg.series.map((s, i) => ({
      label: s.label,
      data: s.data,
      borderColor: colors[i % colors.length],
      tension: 0.2,
      spanGaps: true,
    }));

    new Chart(canvas, {
      type: "line",
      data: { labels: cfg.labels, datasets },
      options: {
        plugins: { legend: { position: "top" } },
        scales:  { y: { title: { display: true, text: "€" } } },
      },
    });
  }

  // ── Initialisation ───────────────────────────────────────────────────────
  function init() {
    // Onglets : remplace les anciens onclick="switchTab(...)"
    document.querySelectorAll("[data-tab]").forEach(btn => {
      btn.addEventListener("click", () => switchTab(btn, btn.dataset.tab));
    });
    // Boutons de visualisation : remplace les anciens onclick="setViz(...)"
    document.querySelectorAll("[data-viz]").forEach(btn => {
      btn.addEventListener("click", () => setViz(btn, btn.dataset.viz));
    });

    brancherCascade("region", "departement");
    brancherCascade("region_2", "departement_2");

    majFiltresComparaison(VIZ_TYPE);
    majIndication(VIZ_TYPE);

    initClassement();
    initCourbe();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();