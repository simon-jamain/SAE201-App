// cascade.js — Met à jour la liste des départements quand la région change

document.getElementById("region").addEventListener("change", async (e) => {
  const regionId = e.target.value;
  const selectDept = document.getElementById("departement");

  // Vider la liste existante
  selectDept.innerHTML = '<option value="">-- Choisir --</option>';

  // Si aucune région sélectionnée, on s'arrête là
  if (!regionId) return;

  // BASE_URL est défini dans accueil.html (vide en local, préfixe en production)
  // NE JAMAIS mettre une URL AJAX avec un / initial codé en dur
  const response = await fetch(`${BASE_URL}/api/departements/${regionId}`);
  const depts = await response.json();

  // Remplir la liste avec les départements reçus
  for (const dept of depts) {
    const opt = document.createElement("option");
    opt.value = dept.id;
    opt.textContent = `${dept.code} – ${dept.libelle}`;
    selectDept.appendChild(opt);
  }
});
