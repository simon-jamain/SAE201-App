const PAGE_SIZE = 15;
let profesData = [];
let currentPage = 1;
const profesEvolution = typeof EVOLUTION !== 'undefined' ? EVOLUTION : [];
const profesParSexe = typeof PAR_SEXE !== 'undefined' ? PAR_SEXE : [];
const profesParAge = typeof PAR_AGE !== 'undefined' ? PAR_AGE : [];

/**
 * Active un onglet de la page professionnels.
 */
function switchTab(e, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  e.currentTarget.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

/**
 * Bascule entre la vue tableau et la vue graphique pour les professionnels.
 */
function switchViz(prefix, type, btn) {
  document.querySelectorAll(`#${prefix}-tab, #${prefix}-graph`).forEach(v => v.classList.remove("active"));
  document.getElementById(`${prefix}-${type}`).classList.add("active");
  btn.closest(".viz-switcher").querySelectorAll(".viz-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

/**
 * Branche la cascade région -> département du formulaire professionnels.
 */
function setupCascade(regionId, deptId) {
  const r = document.getElementById(regionId);
  const d = document.getElementById(deptId);
  if (!r || !d) return;

  r.addEventListener("change", async (e) => {
    const id = e.target.value;
    d.innerHTML = '<option value="">— Tous les départements —</option>';
    if (!id) return;
    try {
      const res = await fetch(`${BASE_URL}/api/departements/${id}`);
      if (!res.ok) throw new Error("Erreur de récupération");
      const depts = await res.json();
      depts.forEach(dept => {
        const o = document.createElement("option");
        o.value = dept.id;
        o.textContent = `${dept.code} – ${dept.libelle}`;
        d.appendChild(o);
      });
    } catch (err) {
      console.error("Erreur cascade :", err);
      d.innerHTML = '<option value="">Erreur de chargement</option>';
    }
  });
}

/**
 * Rend la page courante du tableau des professionnels.
 */
function renderPage() {
  const tbody = document.getElementById("profes-tbody");
  if (!tbody) return;

  const totalPages = Math.max(1, Math.ceil(profesData.length / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRows = profesData.slice(start, start + PAGE_SIZE);

  tbody.innerHTML = pageRows.map(r => `
    <tr>
      <td>${r.annee ? String(r.annee).slice(0,4) : ''}</td>
      <td style="font-weight:600;">${Number(r.effectif ?? 0).toLocaleString('fr-FR')}</td>
      <td>${r.densite != null ? Number(r.densite).toFixed(2) : '—'}</td>
    </tr>
  `).join('');

  const pagination = document.getElementById("profes-pagination");
  const pageInfo   = document.getElementById("profes-page-info");
  const prevBtn    = document.getElementById("profes-prev");
  const nextBtn    = document.getElementById("profes-next");

  if (profesData.length <= PAGE_SIZE) {
    pagination.style.display = 'none';
  } else {
    pagination.style.display = 'flex';
    pageInfo.textContent = `Page ${currentPage} / ${totalPages} (${profesData.length} lignes)`;
  }

  prevBtn.disabled = currentPage <= 1;
  nextBtn.disabled = currentPage >= totalPages;
}

/**
 * Charge les données des professionnels et réinitialise la pagination.
 */
function initProfesTable(data) {
  profesData = data;
  currentPage = 1;
  renderPage();
}

/**
 * Initialise l'anneau de répartition par sexe.
 */
function initSexeChart() {
  if (!profesParSexe.length) return;
  const canvas = document.getElementById("c-sexe");
  if (!canvas || typeof Chart === "undefined") return;

  const colors = ['#1E3A8A','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4','#EC4899','#84CC16'];
  const labels = profesParSexe.map(r => r.libelle_sexe || '');
  const values = profesParSexe.map(r => parseInt(r.effectif) || 0);
  const legend = document.getElementById('legend-sexe');
  if (legend) {
    labels.forEach((label, index) => {
      const entry = document.createElement('span');
      entry.innerHTML = `<b style="background:${colors[index % colors.length]}"></b>${label}`;
      legend.appendChild(entry);
    });
  }

  new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => ' ' + c.label + ' : ' + c.parsed.toLocaleString('fr-FR') } }
      }
    }
  });
}

/**
 * Initialise le camembert de répartition par tranche d'âge.
 */
function initAgeChart() {
  if (!profesParAge.length) return;
  const canvas = document.getElementById("c-age");
  if (!canvas || typeof Chart === "undefined") return;

  const colors = ['#1E3A8A','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4','#EC4899','#84CC16'];
  const labels = profesParAge.map(r => r.libelle_classe_age || '');
  const values = profesParAge.map(r => parseInt(r.effectif) || 0);
  const legend = document.getElementById('legend-age');
  if (legend) {
    labels.forEach((label, index) => {
      const entry = document.createElement('span');
      entry.innerHTML = `<b style="background:${colors[index % colors.length]}"></b>${label}`;
      legend.appendChild(entry);
    });
  }

  new Chart(canvas, {
    type: 'pie',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => ' ' + c.label + ' : ' + c.parsed.toLocaleString('fr-FR') } }
      }
    }
  });
}

/**
 * Initialise la courbe d'évolution de l'effectif et de la densité.
 */
function initEvolutionChart() {
  if (!profesEvolution.length) return;
  const canvas = document.getElementById("c-evo");
  if (!canvas || typeof Chart === "undefined") return;

  const years = profesEvolution.map(d => d.annee ? String(d.annee).slice(0,4) : '');
  const effs  = profesEvolution.map(d => parseInt(d.effectif)  || 0);
  const dens  = profesEvolution.map(d => parseFloat(d.densite) || 0);
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        {label:'Effectif', data:effs, borderColor:'#1E3A8A', backgroundColor:'rgba(30,58,138,.07)', tension:.35, fill:true, pointRadius:4, yAxisID:'y'},
        {label:'Densité',  data:dens, borderColor:'#2563EB', backgroundColor:'rgba(37,99,235,.07)', tension:.35, fill:true, pointRadius:4, borderDash:[5,4], yAxisID:'y1'}
      ]
    },
    options: {
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        y: {position:'left', beginAtZero:false, title:{display:true,text:'Effectif',font:{size:11}}},
        y1:{position:'right', beginAtZero:false, grid:{drawOnChartArea:false}, title:{display:true,text:'Densité',font:{size:11}}}
      }
    }
  });
}

// Initialise les interactions dès que le DOM est prêt.
document.addEventListener("DOMContentLoaded", () => {
  setupCascade("pf-region", "pf-dept");

  const prevBtn = document.getElementById("profes-prev");
  const nextBtn = document.getElementById("profes-next");

  if (prevBtn) prevBtn.addEventListener("click", () => { currentPage--; renderPage(); });
  if (nextBtn) nextBtn.addEventListener("click", () => { currentPage++; renderPage(); });

  if (typeof RESULTATS !== 'undefined' && RESULTATS.length) {
    initProfesTable(RESULTATS);
  }

  initSexeChart();
  initAgeChart();
  initEvolutionChart();
});
