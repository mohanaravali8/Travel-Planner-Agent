/**
 * Atlas Travel Planner — Main JavaScript
 * Theme toggle, navbar scroll, shared utilities
 */

// ── Theme Management ──────────────────────────────────────────────────────────
const THEME_KEY = 'atlas-theme';

function getTheme() {
    return localStorage.getItem(THEME_KEY) ||
           (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    }
    localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

// Apply theme immediately on load (avoid flash)
applyTheme(getTheme());

document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle button
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

    // Navbar scroll effect
    const nav = document.getElementById('mainNav');
    if (nav) {
        const onScroll = () => {
            nav.classList.toggle('scrolled', window.scrollY > 20);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    // Animate elements on scroll
    initScrollAnimations();

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
        });
    });
});

// ── Scroll Animations ─────────────────────────────────────────────────────────
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.destination-card, .travel-type-card, .step-item, .feature-chip').forEach(el => {
        el.classList.add('scroll-animate');
        observer.observe(el);
    });
}

// ── Toast Notifications ───────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;';
        document.body.appendChild(container);
    }

    const colors = { success: '#059669', danger: '#dc2626', warning: '#d97706', info: '#2563eb' };
    const toast  = document.createElement('div');
    toast.style.cssText = `
        background: white; color: #0f172a;
        border-left: 4px solid ${colors[type] || colors.info};
        border-radius: 10px; padding: .8rem 1rem;
        box-shadow: 0 8px 24px rgba(0,0,0,.15);
        font-size: .88rem; max-width: 340px;
        animation: slideUp .3s ease;
        transition: opacity .3s;
    `;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ── Copy to Clipboard ─────────────────────────────────────────────────────────
function copyToClipboard(text, label = 'Copied!') {
    navigator.clipboard.writeText(text).then(() => showToast(label, 'success'));
}

// ── Format Currency ───────────────────────────────────────────────────────────
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount);
}

// ── Navbar scrolled style ─────────────────────────────────────────────────────
const styleEl = document.createElement('style');
styleEl.textContent = `
    .atlas-navbar.scrolled {
        box-shadow: 0 4px 20px rgba(0,0,0,.1);
    }
    .scroll-animate {
        opacity: 0; transform: translateY(20px);
        transition: opacity .5s ease, transform .5s ease;
    }
    .scroll-animate.in-view {
        opacity: 1; transform: translateY(0);
    }
`;
document.head.appendChild(styleEl);
