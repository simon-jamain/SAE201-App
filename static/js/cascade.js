document.getElementById("region").addEventListener("change", async (e) => {
  const regionId  = e.target.value;
  const selectDept = document.getElementById("departement");

  // Vider la liste
  selectDept.innerHTML = '<option value="">-- Choisir --</option>';
  if (!regionId) return;

  try {
    // BASE_URL gère le préfixe en déploiement sous-dossier ; vide en local
    const response = await fetch(`${BASE_URL}/api/departements/${regionId}`);
    if (!response.ok) throw new Error("Réponse serveur non OK");
    const depts = await response.json();

    for (const dept of depts) {
      const opt = document.createElement("option");
      opt.value       = dept.id;
      opt.textContent = `${dept.code} – ${dept.libelle}`;
      selectDept.appendChild(opt);
    }
  } catch (err) {
    console.error("[cascade.js] Erreur :", err);
    selectDept.innerHTML = '<option value="">Erreur de chargement</option>';
  }
});
