const PAGE_SIZE = 15;
let profesData = [];
let currentPage = 1;

function switchTab(e, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  e.currentTarget.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

function switchViz(prefix, type, btn) {
  document.querySelectorAll(`#${prefix}-tab, #${prefix}-graph`).forEach(v => v.classList.remove("active"));
  document.getElementById(`${prefix}-${type}`).classList.add("active");
  btn.closest(".viz-switcher").querySelectorAll(".viz-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

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

function renderPage() {
  const tbody = document.getElementById("profes-tbody");
  if (!tbody) return;

  const totalPages = Math.max(1, Math.ceil(profesData.length / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRows = profesData.slice(start, start + PAGE_SIZE);

  tbody.innerHTML = pageRows.map(r => `
    <tr>
      <td>${r.libelle_sexe ?? ''}</td>
      <td>${r.libelle_classe_age ?? ''}</td>
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

function initProfesTable(data) {
  profesData = data;
  currentPage = 1;
  renderPage();
}

document.addEventListener("DOMContentLoaded", () => {
  setupCascade("pf-region", "pf-dept");

  const prevBtn = document.getElementById("profes-prev");
  const nextBtn = document.getElementById("profes-next");

  if (prevBtn) prevBtn.addEventListener("click", () => { currentPage--; renderPage(); });
  if (nextBtn) nextBtn.addEventListener("click", () => { currentPage++; renderPage(); });

  if (typeof RESULTATS !== 'undefined' && RESULTATS.length) {
    initProfesTable(RESULTATS);
  }
});
