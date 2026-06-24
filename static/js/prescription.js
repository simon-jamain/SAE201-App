const PAGE_SIZE = 15;
let prescriptionData = [];
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
  const tbody = document.getElementById("presc-tbody");
  if (!tbody) return;

  const totalPages = Math.max(1, Math.ceil(prescriptionData.length / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;

  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRows = prescriptionData.slice(start, start + PAGE_SIZE);

  tbody.innerHTML = pageRows.map(r => `
    <tr>
      <td>${r.annee}</td>
      <td style="font-weight:500;">${r.poste}</td>
      <td>${Number(r.nb_prescriptions).toLocaleString('fr-FR')}</td>
      <td style="font-weight:600;color:var(--navy);">${Number(r.montant_total).toLocaleString('fr-FR', {minimumFractionDigits:2, maximumFractionDigits:2})} €</td>
    </tr>
  `).join('');

  const pagination = document.getElementById("presc-pagination");
  const pageInfo   = document.getElementById("presc-page-info");
  const prevBtn    = document.getElementById("presc-prev");
  const nextBtn    = document.getElementById("presc-next");

  if (prescriptionData.length <= PAGE_SIZE) {
    pagination.style.display = 'none';
  } else {
    pagination.style.display = 'flex';
    pageInfo.textContent = `Page ${currentPage} / ${totalPages} (${prescriptionData.length} lignes)`;
  }

  prevBtn.disabled = currentPage <= 1;
  nextBtn.disabled = currentPage >= totalPages;
}

function initPrescriptionTable(data) {
  prescriptionData = data;
  currentPage = 1;
  renderPage();
}

document.addEventListener("DOMContentLoaded", () => {
  setupCascade("pp-region", "pp-dept");

  const prevBtn = document.getElementById("presc-prev");
  const nextBtn = document.getElementById("presc-next");

  if (prevBtn) prevBtn.addEventListener("click", () => { currentPage--; renderPage(); });
  if (nextBtn) nextBtn.addEventListener("click", () => { currentPage++; renderPage(); });

  // Initialise la pagination si des données sont déjà présentes (injectées par Flask)
  if (typeof RESULTATS !== 'undefined' && RESULTATS.length) {
    initPrescriptionTable(RESULTATS);
  }
});
