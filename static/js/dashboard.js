/**
 * Atlas Travel Planner — Dashboard JavaScript
 * Filters, weather widget, destination modal
 */

document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    loadWeather();
    initDestCards();
});

// ── Filter Logic ──────────────────────────────────────────────────────────────
function initFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyFilters();
        });
    });

    const budgetFilter = document.getElementById('budgetFilter');
    if (budgetFilter) {
        budgetFilter.addEventListener('change', applyFilters);
    }
}

function applyFilters() {
    const activeRegion = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
    const budgetFilter = document.getElementById('budgetFilter')?.value || '';

    document.querySelectorAll('.dest-item').forEach(item => {
        const region = item.dataset.region || '';
        const budget = item.dataset.budget || '';

        const regionMatch = activeRegion === 'all' || region === activeRegion;
        const budgetMatch = !budgetFilter || budget === budgetFilter;

        if (regionMatch && budgetMatch) {
            item.style.display = '';
            item.style.animation = 'fadeIn .3s ease';
        } else {
            item.style.display = 'none';
        }
    });

    // Show count
    const visible = document.querySelectorAll('.dest-item:not([style*="display: none"])').length;
    showToast(`Showing ${visible} destination${visible !== 1 ? 's' : ''}`, 'info', 1500);
}

// ── Weather Widget ─────────────────────────────────────────────────────────────
async function loadWeather() {
    const cityInput = document.getElementById('weatherCity');
    const city      = cityInput ? cityInput.value.trim() || 'Paris' : 'Paris';
    const result    = document.getElementById('weatherResult');
    if (!result) return;

    result.innerHTML = `
        <div class="d-flex gap-2 align-items-center">
            <div class="skeleton" style="width:50px;height:50px;border-radius:10px"></div>
            <div style="flex:1">
                <div class="skeleton mb-1" style="height:20px;width:60%"></div>
                <div class="skeleton" style="height:14px;width:40%"></div>
            </div>
        </div>`;

    try {
        const res  = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
        const data = await res.json();

        if (data.success) {
            const iconUrl = `https://openweathermap.org/img/wn/${data.icon}@2x.png`;
            result.innerHTML = `
                <div class="weather-card">
                    <img src="${iconUrl}" width="52" height="52" alt="${data.description}"
                         onerror="this.style.display='none'" />
                    <div>
                        <div class="weather-temp">${data.temp}°C</div>
                        <div class="weather-desc">${data.description}</div>
                        <div style="font-size:.75rem;opacity:.8;margin-top:.2rem">
                            ${data.city}${data.country !== '—' ? ', ' + data.country : ''}
                            · Feels ${data.feels_like}°C
                        </div>
                    </div>
                    <div class="ms-auto text-right" style="font-size:.75rem;opacity:.8">
                        <div>💧 ${data.humidity}%</div>
                        <div>💨 ${data.wind_speed} m/s</div>
                        ${data.mock ? '<div class="mt-1" style="opacity:.6">Sample data</div>' : ''}
                    </div>
                </div>`;
        } else {
            result.innerHTML = `<div class="text-muted small">City not found. Try another.</div>`;
        }
    } catch (err) {
        result.innerHTML = `<div class="text-danger small">Failed to load weather.</div>`;
    }
}

// ── Destination Cards ─────────────────────────────────────────────────────────
function initDestCards() {
    // Add click-to-open for quick weather fetch
    document.querySelectorAll('.dest-item').forEach(card => {
        card.addEventListener('mouseenter', () => {
            const region = card.dataset.region;
            if (region) {
                // Subtle entrance animation
                card.querySelector('.destination-card')?.classList.add('hovered');
            }
        });
    });
}

// ── Destination Detail Modal ──────────────────────────────────────────────────
function showDestDetail(dest) {
    const modal      = new bootstrap.Modal(document.getElementById('destModal'));
    const titleEl    = document.getElementById('destModalTitle');
    const bodyEl     = document.getElementById('destModalBody');
    const ctaEl      = document.getElementById('destModalCTA');

    if (titleEl) titleEl.textContent = `${dest.emoji || '🌍'} ${dest.name}, ${dest.country}`;
    if (ctaEl)   ctaEl.href = `/chat?dest=${encodeURIComponent(dest.name)}`;

    if (bodyEl) {
        // Build budget table
        let budgetRows = '';
        if (dest.avg_costs) {
            const tiers = { budget: '💚 Budget', 'mid-range': '💛 Mid-Range', luxury: '💜 Luxury' };
            Object.entries(tiers).forEach(([tier, label]) => {
                const costs = dest.avg_costs[tier];
                if (costs) {
                    const daily = Object.values(costs).reduce((s, v) => s + v, 0);
                    budgetRows += `<tr><td>${label}</td><td>$${daily}/day per person</td></tr>`;
                }
            });
        }

        // Highlights
        const highlights = (dest.highlights || []).map(h => `<span class="highlight-tag">${h}</span>`).join('');

        // Cuisine
        const cuisine = (dest.cuisine || []).map(c => `<span class="highlight-tag">🍽️ ${c}</span>`).join('');

        bodyEl.innerHTML = `
            <div class="row g-3">
                <div class="col-12">
                    <img src="${dest.image_url || ''}" class="w-100 rounded-3 mb-3" style="height:200px;object-fit:cover"
                         alt="${dest.name}" onerror="this.style.display='none'" />
                </div>
                <div class="col-md-6">
                    <h6 class="fw-bold text-primary">📍 Overview</h6>
                    <p class="small">${dest.description || ''}</p>
                    <div class="small mb-2"><strong>Best Season:</strong> ${dest.best_season || 'Year-round'}</div>
                    <div class="small mb-2"><strong>Language:</strong> ${dest.language || '—'}</div>
                    <div class="small mb-2"><strong>Currency:</strong> ${dest.currency || '—'}</div>
                    <div class="small mb-2"><strong>Timezone:</strong> ${dest.timezone || '—'}</div>
                    <div class="small"><strong>Safety:</strong> ${dest.safety || '—'}</div>
                </div>
                <div class="col-md-6">
                    <h6 class="fw-bold text-primary">💰 Budget Estimates (Daily)</h6>
                    <table class="table table-sm table-bordered" style="font-size:.82rem">
                        <tbody>${budgetRows}</tbody>
                    </table>
                    <h6 class="fw-bold text-primary mt-3">📋 Visa</h6>
                    <p class="small">${dest.visa || 'Check official embassy website.'}</p>
                </div>
                <div class="col-12">
                    <h6 class="fw-bold text-primary">🏆 Top Highlights</h6>
                    <div class="d-flex flex-wrap gap-2 mb-3">${highlights}</div>
                    <h6 class="fw-bold text-primary">🍜 Local Cuisine</h6>
                    <div class="d-flex flex-wrap gap-2">${cuisine}</div>
                </div>
            </div>`;
    }

    modal.show();
}
