/* ═══════════════════════════════════════════════════════
   ECI — Shared Components (Header, Footer, Theme, Nav)
   ═══════════════════════════════════════════════════════ */

// ── Logo helpers — transparent PNGs ──
// The full-lockup PNG is 2000×2000 with the "ESSEC [sail] ICI" content
// centred in the canvas (~30% height, ~70% width). We wrap it in a
// clipping container so only the live artwork shows — no dead whitespace.
function eciLogoFull(base) {
  return `<span class="eci-logo-full-wrap" aria-hidden="true">
    <img src="${base}logo-full-remove-bg-io.png" alt="ESSEC Capital Investments" class="eci-logo-full">
  </span>`;
}
// Footer: sail mark icon only
function eciLogoIcon(base) {
  return `<img src="${base}logo-icon-remove-bg-io.png" alt="" aria-hidden="true" class="eci-logo-icon">`;
}

const LINKEDIN_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>`;
const INSTAGRAM_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>`;
const TWITTER_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l11.733 16h4.267l-11.733 -16h-4.267z"/><path d="M4 20l6.768 -6.768m2.46 -2.46l6.772 -6.772"/></svg>`;
const MAIL_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>`;
const MENU_ICON = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>`;
const CLOSE_ICON = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
const CHEVRON_DOWN = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`;

// Determine current page for active nav
function getCurrentPage() {
  const path = window.location.pathname;
  const file = path.split('/').pop() || 'index.html';
  return file;
}

function getBasePath() {
  const path = window.location.pathname;
  if (path.includes('/pages/')) return '../';
  return './';
}

// ── Nav Items ──
const NAV_ITEMS = [
  { label: 'Home',           href: 'index.html' },
  { label: 'About',          href: 'pages/about.html' },
  { label: 'Team',           href: 'pages/team.html' },
  { label: 'Pitches',        href: 'pages/pitches.html' },
  { label: 'Fund',           href: 'pages/fund.html' },
  { label: 'Join Us',        href: 'pages/join.html' },
  { label: 'Contact',        href: 'pages/contact.html' },
];

// ── Render Header ──
function renderHeader() {
  const current = getCurrentPage();
  const base = getBasePath();
  
  const navLinks = NAV_ITEMS.map(item => {
    const file = item.href.split('/').pop();
    const active = (current === file || (current === '' && file === 'index.html')) ? ' active' : '';
    return `<li><a href="${base}${item.href}"${active ? ` class="${active.trim()}"` : ''}>${item.label}</a></li>`;
  }).join('');

  const mobileLinks = NAV_ITEMS.map(item => {
    const file = item.href.split('/').pop();
    return `<a href="${base}${item.href}">${item.label}</a>`;
  }).join('');

  return `
  <a href="#main" class="skip-link">Skip to content</a>
  <header class="site-header" id="site-header">
    <div class="header-inner">
      <a href="${base}index.html" class="logo" aria-label="ECI Home">
        ${eciLogoFull(base)}
      </a>
      <nav aria-label="Main navigation">
        <ul class="nav-desktop" role="list">${navLinks}</ul>
      </nav>
      <div class="nav-actions">
        <button class="theme-toggle" data-theme-toggle aria-label="Switch theme">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>
        <button class="mobile-menu-btn" aria-label="Open menu" onclick="toggleMobileNav(true)">
          ${MENU_ICON}
        </button>
      </div>
    </div>
  </header>
  <div class="mobile-nav" id="mobile-nav" role="dialog" aria-label="Mobile navigation">
    <div class="mobile-nav-header">
      <a href="${base}index.html" class="logo" aria-label="ECI Home">${eciLogoFull(base)}</a>
      <button class="mobile-menu-btn" aria-label="Close menu" onclick="toggleMobileNav(false)">${CLOSE_ICON}</button>
    </div>
    ${mobileLinks}
  </div>`;
}

// ── Render Footer ──
function renderFooter() {
  const base = getBasePath();
  return `
  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-col footer-brand">
          <div class="logo mb-4" style="color:inherit;gap:var(--space-2);">${eciLogoIcon(base)}<span>ECI</span></div>
          <p>ESSEC Capital Investments is a student-led investment association at ESSEC Business School dedicated to equity research, stock pitches, and financial education.</p>
          <div class="footer-social mt-4">
            <a href="https://www.linkedin.com/company/essec-capital-investments-eci/" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">${LINKEDIN_ICON}</a>
            <a href="mailto:esseccapitalinvestments@gmail.com" aria-label="Email">${MAIL_ICON}</a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Navigate</h4>
          <ul role="list">
            <li><a href="${base}index.html">Home</a></li>
            <li><a href="${base}pages/about.html">About ECI</a></li>
            <li><a href="${base}pages/team.html">The Team</a></li>
            <li><a href="${base}pages/pitches.html">Our Pitches</a></li>
            <li><a href="${base}pages/fund.html">Our Fund</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Get Involved</h4>
          <ul role="list">
            <li><a href="${base}pages/join.html">Join Us</a></li>
            <li><a href="${base}pages/partners.html">Partners</a></li>
            <li><a href="${base}pages/contact.html">Contact</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Stay in touch</h4>
          <p style="font-size:var(--text-sm);opacity:0.7;margin-bottom:var(--space-2);">Follow us on LinkedIn for our latest pitches and events.</p>
          <a href="https://www.linkedin.com/company/essec-capital-investments-eci/" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:var(--space-2);font-size:var(--text-sm);font-weight:600;color:inherit;text-decoration:none;opacity:0.9;">${LINKEDIN_ICON} Follow on LinkedIn</a>
        </div>
      </div>
      <div class="footer-bottom">
        <span>&copy; 2025 ESSEC Capital Investments (ECI). All rights reserved.</span>
        <div style="display:flex;gap:var(--space-4);">
          <a href="${base}pages/contact.html" style="color:inherit;text-decoration:none;">Contact Us</a>
        </div>
      </div>
    </div>
  </footer>`;
}

// ── Mobile Nav ──
function toggleMobileNav(open) {
  const nav = document.getElementById('mobile-nav');
  if (open) {
    nav.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  } else {
    nav.classList.remove('is-open');
    document.body.style.overflow = '';
  }
}

// ── Theme Toggle ──
// ── Theme ── (apply immediately so no flash)
var _eciTheme = (function() {
  var saved = localStorage.getItem('eci-theme');
  var theme = saved || 'light';
  document.documentElement.setAttribute('data-theme', theme);

  function updateToggleIcon(btn, th) {
    btn.innerHTML = th === 'dark'
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    btn.setAttribute('aria-label', 'Switch to ' + (th === 'dark' ? 'light' : 'dark') + ' mode');
  }

  // Called after header is injected
  function initToggle() {
    var toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;
    updateToggleIcon(toggle, theme);
    toggle.addEventListener('click', function() {
      theme = theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('eci-theme', theme);
      updateToggleIcon(toggle, theme);
    });
    // Scroll header shadow
    var header = document.getElementById('site-header');
    if (header) {
      window.addEventListener('scroll', function() {
        header.classList.toggle('site-header--scrolled', window.scrollY > 10);
      }, { passive: true });
    }
  }

  return { initToggle: initToggle };
})();

// ── FAQ Accordion ──
function initFAQ() {
  document.querySelectorAll('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const wasOpen = item.classList.contains('open');
      // Close all
      document.querySelectorAll('.faq-item.open').forEach(el => el.classList.remove('open'));
      // Toggle
      if (!wasOpen) item.classList.add('open');
    });
  });
}

// ── Filter System ──
function initFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const filterGroup = btn.closest('.filter-bar');
      filterGroup.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const filter = btn.dataset.filter;
      const cards = document.querySelectorAll('[data-sector]');
      cards.forEach(card => {
        if (filter === 'all' || card.dataset.sector === filter) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

// ── Scroll Reveal (IntersectionObserver) ──
function initScrollReveal() {
  const els = document.querySelectorAll('.fade-in');
  if (!els.length) return;
  els.forEach(el => el.classList.add('will-animate'));
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
  els.forEach(el => observer.observe(el));
}

// ── Inject Header/Footer ──
document.addEventListener('DOMContentLoaded', function() {
  var headerSlot = document.getElementById('header-slot');
  var footerSlot = document.getElementById('footer-slot');
  if (headerSlot) headerSlot.innerHTML = renderHeader();
  if (footerSlot) footerSlot.innerHTML = renderFooter();

  // Wire theme toggle AFTER header is in the DOM
  _eciTheme.initToggle();

  // Re-init FAQ if present
  if (document.querySelector('.faq-item')) initFAQ();
  if (document.querySelector('.filter-btn')) initFilters();
  initScrollReveal();
});
