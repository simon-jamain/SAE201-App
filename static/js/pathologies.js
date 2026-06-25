let currentViz = 'table';
let currentMapMode = 'region';
let pathologiesData = [];
let currentTableData = [];
let tablePage = 1;
const tablePageSize = 15;

const apiPathologiesUrl = window.PATHOLOGIES_CONFIG?.apiPathologiesUrl || '';
const apiRegionsUrl = window.PATHOLOGIES_CONFIG?.apiRegionsUrl || '';
const apiDepartmentsBaseUrl = window.PATHOLOGIES_CONFIG?.apiDepartmentsBaseUrl || '';

function switchTab(e, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  e.currentTarget.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

function setViz(e, type) {
  currentViz = type;
  document.querySelectorAll('.viz-btn').forEach(b => b.classList.remove('active'));
  e.currentTarget.classList.add('active');
  updateViz();
}

async function fetchPathologyLabels(year) {
  const params = new URLSearchParams();
  if (year) params.set('year', year);
  params.set('distinct', '1');
  const resp = await fetch(`${apiPathologiesUrl}?${params.toString()}`);
  if (!resp.ok) {
    console.error('Impossible de charger la liste des pathologies', resp.statusText);
    return [];
  }
  return await resp.json();
}

async function fetchRegions() {
  const resp = await fetch(apiRegionsUrl);
  if (!resp.ok) {
    console.error('Impossible de charger la liste des régions', resp.statusText);
    return [];
  }
  // Double sécurité côté client : si l'API renvoie encore France, on la retire ici.
  return (await resp.json()).filter(region => {
    const code = String(region.code || '').trim();
    const label = String(region.libelle || '').trim().toLowerCase();
    return code !== '999' && label !== 'france';
  });
}

async function fetchDepartments(region) {
  const url = `${apiDepartmentsBaseUrl.replace(/0$/, '')}${region}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    console.error('Impossible de charger la liste des départements', resp.statusText);
    return [];
  }
  return await resp.json();
}

async function fetchPathologiesData(year, pathologie, region, departement) {
  const params = new URLSearchParams();
  if (year) params.set('year', year);
  if (pathologie && pathologie !== 'all') params.set('pathologie', pathologie);
  if (region && region !== 'all') params.set('region', region);
  if (departement && departement !== 'all') params.set('departement', departement);
  const resp = await fetch(`${apiPathologiesUrl}?${params.toString()}`);
  if (!resp.ok) {
    console.error('Impossible de charger les données pathologies', resp.statusText);
    return [];
  }
  return await resp.json();
}

function populatePathologySelect(pathos) {
  const select = document.getElementById('sel-pathology');
  const selected = select.value || 'all';
  select.innerHTML = '<option value="all">Toutes les pathologies</option>' +
    pathos.map(patho => `
      <option value="${patho}">${patho}</option>
    `).join('');
  if (pathos.includes(selected)) {
    select.value = selected;
  }
}

function populateRegionSelect(regions) {
  const select = document.getElementById('sel-region');
  const selected = select.value || 'all';
  select.innerHTML = '<option value="all">Toutes les régions</option>' +
    regions.map(region => `
      <option value="${region.id}" data-code="${region.code}">${region.libelle}</option>
    `).join('');
  if (regions.some(r => String(r.id) === selected)) {
    select.value = selected;
  }
}

function populateDepartmentSelect(departments) {
  const select = document.getElementById('sel-departement');
  const selected = select.value || 'all';
  select.innerHTML = '<option value="all">Tous les départements</option>' +
    departments.map(dept => `
      <option value="${dept.code}">${dept.libelle}</option>
    `).join('');
  if (departments.some(d => d.code === selected)) {
    select.value = selected;
  }
}

function getIndicatorLabel(ind) {
  return {
    nombre_patients: 'Nombre de patients',
    taux_prevalence: 'Taux de prévalence (%)',
  }[ind] || ind;
}

function displayRegionLabel(row) {
  return row.region_libelle || row.region || '';
}

function displayPathologyLabel(row) {
  return row.pathologie || 'Non renseignée';
}

function isOutreMerRegion(row) {
  const outreMerCodes = new Set(['01', '02', '03', '04', '06']);
  return row.region && outreMerCodes.has(row.region.toString().padStart(2, '0'));
}

function displayDepartementLabel(row) {
  if (isOutreMerRegion(row)) {
    return '';
  }
  return row.departement_libelle || row.departement || '';
}

function formatValue(val, ind) {
  if (ind === 'nombre_patients') return Number(val).toLocaleString('fr-FR');
  if (ind === 'taux_prevalence') return Number(val).toFixed(2) + ' %';
  return val;
}

function getSelectedYear() {
  const yearValue = document.getElementById('sel-year').value;
  return yearValue === 'all' ? null : Number(yearValue);
}

function getFilteredData() {
  const year = getSelectedYear();
  const path = document.getElementById('sel-pathology').value;
  return pathologiesData.filter(d => {
    const rowYear = d.annee != null ? Number(d.annee) : null;
    return (!year || rowYear === year) &&
           (path === 'all' || d.pathologie === path);
  });
}

function getFilteredDataForChart() {
  const path = document.getElementById('sel-pathology').value;
  return pathologiesData.filter(d => {
    return (path === 'all' || d.pathologie === path);
  });
}

async function updateViz() {
  const ind = document.getElementById('sel-indicator').value;
  const year = getSelectedYear();
  const path = document.getElementById('sel-pathology').value;
  const regionSelect = document.getElementById('sel-region');
  const regionId = regionSelect.value;
  const region = regionId !== 'all' ? regionSelect.selectedOptions[0]?.dataset.code : null;
  const departement = document.getElementById('sel-departement').value;
  
  if (currentViz === 'chart') {
    let regionToFetch = null;
    let deptToFetch = null;
    if (regionId !== 'all' && region) {
      regionToFetch = region;
      if (departement !== 'all') {
        deptToFetch = departement;
      }
    }
    pathologiesData = await fetchPathologiesData(null, path, regionToFetch, deptToFetch);
  } else if (currentViz === 'map') {
    pathologiesData = await fetchPathologiesData(year, path, null, null);
  } else {
    pathologiesData = await fetchPathologiesData(year, path, region, departement);
  }
  
  const data = currentViz === 'chart' ? getFilteredDataForChart() : getFilteredData();
  document.getElementById('viz-table').style.display = 'none';
  document.getElementById('viz-chart').style.display = 'none';
  document.getElementById('viz-map').style.display = 'none';
  if (currentViz === 'table') renderTable(data, ind);
  if (currentViz === 'chart') renderChart(data, ind, regionId === 'all', departement === 'all');
  if (currentViz === 'map') renderMap(data, ind);
}

function renderTable(data, ind) {
  document.getElementById('viz-table').style.display = 'block';
  document.getElementById('th-indicator').textContent = getIndicatorLabel(ind);
  currentTableData = data;
  tablePage = 1;
  renderCurrentTablePage(ind);
}

function renderCurrentTablePage(ind) {
  const totalRows = currentTableData.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / tablePageSize));
  if (tablePage > totalPages) tablePage = totalPages;

  const start = (tablePage - 1) * tablePageSize;
  const end = start + tablePageSize;
  const pageData = currentTableData.slice(start, end);

  document.getElementById('table-body').innerHTML = pageData.map(row => `
    <tr>
      <td>${displayRegionLabel(row)}</td><td>${displayPathologyLabel(row)}</td>
      <td>${displayDepartementLabel(row)}</td><td>${row.annee}</td>
      <td style="text-align:right;">${formatValue(row[ind], ind)}</td>
    </tr>
  `).join('');

  const pagination = document.getElementById('patho-table-pagination');
  const pageInfo = document.getElementById('patho-page-info');
  const prevBtn = document.getElementById('patho-prev-page');
  const nextBtn = document.getElementById('patho-next-page');

  if (totalRows <= tablePageSize) {
    pagination.style.display = 'none';
  } else {
    pagination.style.display = 'flex';
    pageInfo.textContent = `Page ${tablePage} / ${totalPages} (${totalRows} lignes)`;
  }

  prevBtn.disabled = tablePage <= 1;
  nextBtn.disabled = tablePage >= totalPages;
}

function renderChart(data, ind, groupByRegion, groupByDept) {
  document.getElementById('viz-chart').style.display = 'block';
  const emptyState = document.getElementById('chart-empty');
  const canvas = document.getElementById('chart-canvas');

  if (!data.length) {
    emptyState.style.display = 'block';
    canvas.style.display = 'none';
    return;
  }
  
  canvas.style.display = 'block';
  emptyState.style.display = 'none';

  const ctx = canvas.getContext('2d');
  const indicatorLabel = getIndicatorLabel(ind);
  const colors = ['#1E3A8A', '#16A34A', '#DC2626', '#F59E0B', '#7C3AED', '#0891B2', '#BE123C', '#65A30D', '#0F766E', '#4F46E5', '#059669', '#E11D48', '#EAB308'];

  let allYears = new Set();
  let groupedData = {};
  let groupLabel = '';

  if (groupByRegion) {
    groupLabel = 'Région';
    data.forEach(row => {
      const year = row.annee || new Date().getFullYear();
      allYears.add(year);
      const regionName = displayRegionLabel(row) || 'Inconnue';
      if (!groupedData[regionName]) groupedData[regionName] = {};
      groupedData[regionName][year] = (groupedData[regionName][year] || 0) + Number(row[ind] || 0);
    });
  } else if (groupByDept) {
    groupLabel = 'Département';
    data.forEach(row => {
      const year = row.annee || new Date().getFullYear();
      allYears.add(year);
      const deptName = displayDepartementLabel(row) || displayRegionLabel(row) || 'Inconnu';
      if (!groupedData[deptName]) groupedData[deptName] = {};
      groupedData[deptName][year] = (groupedData[deptName][year] || 0) + Number(row[ind] || 0);
    });
  } else {
    data.forEach(row => {
      const year = row.annee || new Date().getFullYear();
      allYears.add(year);
      if (!groupedData['global']) groupedData['global'] = {};
      groupedData['global'][year] = (groupedData['global'][year] || 0) + Number(row[ind] || 0);
    });
  }

  const years = Array.from(allYears).sort((a, b) => Number(a) - Number(b));
  const groups = Object.keys(groupedData).sort((a, b) => a.localeCompare(b, 'fr'));
  const datasets = groups.map((group, idx) => ({
    label: group === 'global' ? indicatorLabel : `${groupLabel}: ${group}`,
    data: years.map(year => groupedData[group][year] || 0),
    borderColor: colors[idx % colors.length],
    backgroundColor: colors[idx % colors.length] + '14',
    borderWidth: 2.5,
    tension: 0.15,
    fill: false,
    pointRadius: 4,
    pointHoverRadius: 6,
  }));

  if (window.pathologiesChart) {
    window.pathologiesChart.destroy();
  }

  window.pathologiesChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: years,
      datasets: datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label} : ${formatValue(context.raw, ind)}`,
          },
        },
      },
      scales: {
        x: { title: { display: true, text: 'Années disponibles' } },
        y: { beginAtZero: true, title: { display: true, text: indicatorLabel } },
      },
    },
  });
}

const mapGeoJsonCache = { region: null, departement: null };

async function loadFranceGeoJson(type) {
  if (mapGeoJsonCache[type]) return mapGeoJsonCache[type];
  const urls = {
    region: 'https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson',
    departement: 'https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson',
  };
  const resp = await fetch(urls[type]);
  if (!resp.ok) {
    console.error('Impossible de charger le geojson de la France', resp.statusText);
    return null;
  }
  mapGeoJsonCache[type] = await resp.json();
  return mapGeoJsonCache[type];
}

function setMapMode(mode) {
  currentMapMode = mode;
  updateViz();
}

async function renderMap(data, ind) {
  document.getElementById('viz-map').style.display = 'block';
  const buckets = {};
  data.forEach(d => {
    const code = currentMapMode === 'region'
      ? String(d.region || '').padStart(2, '0')
      : String(d.departement || '').padStart(2, '0');
    const label = currentMapMode === 'region'
      ? (d.region_libelle || d.region || 'Inconnue')
      : (d.departement_libelle || d.departement || 'Inconnu');
    if (!code) return;
    if (!buckets[code]) buckets[code] = { sum: 0, count: 0, label, values: [] };
    buckets[code].sum += Number(d[ind] || 0);
    buckets[code].count += 1;
    buckets[code].values.push(Number(d[ind] || 0));
  });
  const features = Object.entries(buckets).map(([code, value]) => ({
    code,
    label: value.label,
    value: ind === 'nombre_patients'
      ? value.sum
      : (value.count ? value.values.reduce((acc, cur) => acc + cur, 0) / value.count : 0),
  }));
  if (!features.length) {
    document.getElementById('plotly-div').innerHTML = '<div class="map-empty">Aucune donnée disponible pour cette sélection.</div>';
    return;
  }
  const france = await loadFranceGeoJson(currentMapMode);
  if (!france) {
    document.getElementById('plotly-div').innerHTML = '<div class="map-empty">Impossible de charger la carte de France.</div>';
    return;
  }
  const locations = features.map(f => f.code);
  const z = features.map(f => f.value);
  const hovertext = features.map(f => f.label);
  const trace = {
    type: 'choropleth',
    geojson: france,
    locations,
    z,
    featureidkey: 'properties.code',
    colorscale: 'Portland',
    marker: { line: { width: 0.5, color: 'white' } },
    colorbar: { title: getIndicatorLabel(ind), thicknessmode: 'fraction', thickness: 0.03 },
    hovertext,
    hovertemplate: '<b>%{hovertext}</b><br>' + `${getIndicatorLabel(ind)}: %{z}<extra></extra>`,
  };
  const layout = {
    title: { text: `Carte de France – ${getIndicatorLabel(ind)} (${currentMapMode === 'region' ? 'régions' : 'départements'})`, font: { size: 18 } },
    geo: {
      scope: 'europe',
      projection: { type: 'mercator' },
      showland: true,
      landcolor: '#f2f2f2',
      showframe: false,
      showcountries: false,
      fitbounds: 'locations',
    },
    margin: { t: 70, l: 0, r: 0, b: 0 },
  };
  Plotly.react('plotly-div', [trace], layout, { responsive: true });
}

async function onRegionChange() {
  const regionSelect = document.getElementById('sel-region');
  const regionId = regionSelect.value;
  const departments = regionId && regionId !== 'all' ? await fetchDepartments(regionId) : [];
  populateDepartmentSelect(departments);
  updateViz();
}

async function initializePathologies() {
  const year = getSelectedYear();
  const labels = await fetchPathologyLabels(year);
  populatePathologySelect(labels);
  const regions = await fetchRegions();
  populateRegionSelect(regions);
  const departments = [];
  populateDepartmentSelect(departments);
  await updateViz();
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('sel-year').addEventListener('change', async () => {
    await initializePathologies();
  });
  document.getElementById('sel-pathology').addEventListener('change', updateViz);
  document.getElementById('sel-region').addEventListener('change', onRegionChange);
  document.getElementById('sel-departement').addEventListener('change', updateViz);
  document.getElementById('sel-indicator').addEventListener('change', updateViz);

  document.getElementById('patho-prev-page').addEventListener('click', () => {
    if (tablePage <= 1) return;
    tablePage -= 1;
    renderCurrentTablePage(document.getElementById('sel-indicator').value);
  });

  document.getElementById('patho-next-page').addEventListener('click', () => {
    const totalPages = Math.max(1, Math.ceil(currentTableData.length / tablePageSize));
    if (tablePage >= totalPages) return;
    tablePage += 1;
    renderCurrentTablePage(document.getElementById('sel-indicator').value);
  });

  initializePathologies();
});
