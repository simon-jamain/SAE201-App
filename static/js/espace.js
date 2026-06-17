/* espace.js — page "Mon espace" (surveillance de la grippe, courbe multi-saisons) */

(function () {
  "use strict";

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

  function initCourbe() {
    const rows = lireJSON("data-evolution");
    if (!rows || rows.length === 0) return;

    const canvas = document.getElementById("courbe-grippe");
    if (!canvas || typeof Chart === "undefined") return;

    const labels = rows.map(r => r.semaine);

    new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Taux de passages aux urgences",
            data: rows.map(r => r.taux_passages_grippe_sau),
            borderColor: "#2E74B5",
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.15,
            spanGaps: true,
          },
          {
            label: "Taux d'hospitalisations",
            data: rows.map(r => r.taux_hospit_grippe_sau),
            borderColor: "#E05A2B",
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.15,
            spanGaps: true,
          },
        ],
      },
      options: {
        plugins: { legend: { position: "top" } },
        scales: {
          y: { title: { display: true, text: "Taux / 100 000" } },
          x: {
            ticks: {
              // Avec ~330 semaines, on n'affiche qu'un repère toutes les ~13
              // semaines (environ une fois par saison) pour rester lisible.
              maxTicksLimit: 24,
              autoSkip: true,
            },
          },
        },
      },
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCourbe);
  } else {
    initCourbe();
  }
})();