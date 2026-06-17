const navHTML = `
  <header>
    <div class="header-inner">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      </svg>
      <span>AMELI Data</span>
    </div>
  </header>
  <div class="nav-gap"></div>
  <nav>
    <div class="nav-inner">
      <div class="nav-list">
        <a href="/">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          Accueil
        </a>
        <a href="/presentation.html">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Présentation d'AMELI
        </a>
        <a href="/medicaments">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          Prescription
        </a>
        <a href="/pathologies">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          Pathologies
        </a>
        <a href="/professionnels">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          Professionnels de santé libéraux
        </a>
        <a href="/contact">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          Contact
        </a>
      </div>
    </div>
  </nav>
`;

document.body.insertAdjacentHTML('afterbegin', navHTML);

// Marque le lien actif selon la page courante
let currentFile = location.pathname.split('/').pop();
if (currentFile === '') {
  currentFile = 'accueil.html';
}
document.querySelectorAll('.nav-list a').forEach(a => {
  const href = a.getAttribute('href');
  if (href === currentFile) {
    a.classList.add('active');
  }
});