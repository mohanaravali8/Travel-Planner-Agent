/**
 * Atlas Travel Planner — Trip Planner JavaScript
 * Form handling, itinerary generation, budget calculator
 */

// Destination data for quick info (populated from template)
const DESTINATIONS = [];

document.addEventListener('DOMContentLoaded', () => {
    initPlannerForm();
    initBudgetPreview();
    initDestinationSearch();
    setMinDate();
});

// ── Set min date to today ──────────────────────────────────────────────────────
function setMinDate() {
    const dateInput = document.getElementById('planStartDate');
    if (dateInput) {
        dateInput.min = new Date().toISOString().split('T')[0];
    }
}

// ── Budget Preview (live) ──────────────────────────────────────────────────────
function initBudgetPreview() {
    const fields = ['planDestination', 'planDuration', 'planBudget', 'planGroupSize'];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', debounce(updateBudgetPreview, 600));
        if (el) el.addEventListener('change', debounce(updateBudgetPreview, 300));
    });

    document.querySelectorAll('input[name="travelType"]').forEach(r => {
        r.addEventListener('change', debounce(updateBudgetPreview, 300));
    });
}

async function updateBudgetPreview() {
    const dest      = document.getElementById('planDestination')?.value?.trim();
    const duration  = document.getElementById('planDuration')?.value || '7';
    const groupSize = document.getElementById('planGroupSize')?.value || '2';
    const travelType= document.querySelector('input[name="travelType"]:checked')?.value || 'mid-range';
    const breakdown = document.getElementById('budgetBreakdown');

    if (!dest || !breakdown) return;

    // Show skeleton
    breakdown.innerHTML = Array(5).fill('<div class="budget-row"><div class="skeleton" style="height:18px;width:60%"></div><div class="skeleton" style="height:18px;width:25%"></div></div>').join('');

    try {
        const res  = await fetch('/api/budget', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ destination: dest, duration, group_size: groupSize, travel_type: travelType }),
        });
        const data = await res.json();

        if (data.budget) {
            const b = data.budget;
            const cur = data.currency || 'USD';
            breakdown.innerHTML = `
                <div class="budget-row"><span class="label">🏨 Accommodation</span><span class="value">${fmt(b.accommodation, cur)}</span></div>
                <div class="budget-row"><span class="label">🍜 Food</span><span class="value">${fmt(b.food, cur)}</span></div>
                <div class="budget-row"><span class="label">🎯 Activities</span><span class="value">${fmt(b.activities, cur)}</span></div>
                <div class="budget-row"><span class="label">🚌 Transport</span><span class="value">${fmt(b.transport, cur)}</span></div>
                <div class="budget-row"><span class="label">📦 Miscellaneous</span><span class="value">${fmt(b.miscellaneous, cur)}</span></div>
                <div class="budget-row" style="border-top:2px solid var(--border);margin-top:.5rem;padding-top:.5rem">
                    <span class="label fw-bold">💰 Total (${groupSize} pax)</span>
                    <span class="value fw-bold text-primary">${fmt(b.total, cur)}</span>
                </div>
                <div class="budget-row text-muted" style="font-size:.78rem">
                    <span>Per person</span>
                    <span>${fmt(b.per_person, cur)}</span>
                </div>`;
        }
    } catch (err) {
        breakdown.innerHTML = `<div class="text-muted small text-center py-2">Enter destination to see estimate</div>`;
    }
}

function fmt(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount || 0);
}

// ── Destination Quick Card ─────────────────────────────────────────────────────
function initDestinationSearch() {
    const destInput = document.getElementById('planDestination');
    if (!destInput) return;

    destInput.addEventListener('change', () => {
        const val   = destInput.value.toLowerCase();
        const match = window._destData?.find(d => d.name.toLowerCase() === val.split(',')[0].trim());
        if (match) showDestQuickCard(match);
        else document.getElementById('destQuickCard').style.display = 'none';
    });
}

function showDestQuickCard(dest) {
    const card   = document.getElementById('destQuickCard');
    const header = document.getElementById('destQuickHeader');
    const body   = document.getElementById('destQuickBody');
    if (!card) return;

    if (header) header.innerHTML = `${dest.emoji || '🌍'} ${dest.name}, ${dest.country} <span class="ms-2 badge bg-primary">${dest.rating} ⭐</span>`;
    if (body) {
        body.innerHTML = `
            <p class="small mb-2">${dest.tagline}</p>
            <div class="small mb-1"><i class="bi bi-calendar-check text-success me-1"></i><strong>Best time:</strong> ${dest.best_season}</div>
            <div class="small mb-1"><i class="bi bi-shield-check text-success me-1"></i><strong>Safety:</strong> ${dest.safety}</div>
            <div class="small"><i class="bi bi-passport text-primary me-1"></i><strong>Visa:</strong> ${dest.visa}</div>`;
    }

    card.style.display = '';
}

// ── Planner Form Submission ────────────────────────────────────────────────────
function initPlannerForm() {
    const form = document.getElementById('plannerForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await generateItinerary();
    });
}

async function generateItinerary() {
    const destination = document.getElementById('planDestination')?.value?.trim();
    if (!destination) {
        showToast('Please enter a destination.', 'warning');
        document.getElementById('planDestination')?.focus();
        return;
    }

    const duration   = document.getElementById('planDuration')?.value || '7';
    const budget     = document.getElementById('planBudget')?.value || '2000';
    const groupSize  = document.getElementById('planGroupSize')?.value || '2';
    const startDate  = document.getElementById('planStartDate')?.value || '';
    const travelType = document.querySelector('input[name="travelType"]:checked')?.value || 'cultural';
    const special    = document.getElementById('planSpecial')?.value?.trim() || '';

    const interests = Array.from(document.querySelectorAll('input[name="interests"]:checked'))
        .map(cb => cb.value);

    // Build included sections list
    const includes = [];
    if (document.getElementById('incHotels')?.checked)    includes.push('hotel recommendations');
    if (document.getElementById('incFood')?.checked)      includes.push('restaurant suggestions');
    if (document.getElementById('incVisa')?.checked)      includes.push('visa information');
    if (document.getElementById('incPacking')?.checked)   includes.push('packing checklist');
    if (document.getElementById('incWeather')?.checked)   includes.push('weather and climate tips');
    if (document.getElementById('incTransport')?.checked) includes.push('transport options');

    // UI: button loading
    const btn = document.getElementById('generateBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>IBM Granite is crafting your itinerary...';
    }

    // Show output section with skeleton
    const outputSection = document.getElementById('itineraryOutput');
    const outputContent = document.getElementById('itineraryContent');
    if (outputSection) outputSection.style.display = '';
    if (outputContent) {
        outputContent.innerHTML = `
            <div class="p-4">
                ${Array(8).fill('<div class="skeleton mb-3" style="height:18px;border-radius:4px"></div>').join('')}
                ${Array(4).fill('<div class="skeleton mb-2" style="height:14px;border-radius:4px;width:80%"></div>').join('')}
                <div class="text-center text-muted mt-4"><i class="bi bi-cpu fs-2 d-block mb-2"></i>IBM Granite AI is generating your personalized itinerary...</div>
            </div>`;

        // Scroll to it
        outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    try {
        const res = await fetch('/api/itinerary', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                destination, duration, budget, group_size: groupSize,
                start_date: startDate, travel_type: travelType,
                interests, special_requirements: special,
                include: includes,
            }),
        });

        const data = await res.json();

        if (data.itinerary && outputContent) {
            const rendered = typeof marked !== 'undefined'
                ? marked.parse(data.itinerary)
                : data.itinerary.replace(/\n/g, '<br>');

            outputContent.innerHTML = rendered;

            // Update refine CTA
            const refineCTA = document.getElementById('refineCTA');
            if (refineCTA) {
                refineCTA.href = `/chat?q=${encodeURIComponent('Refine my ' + duration + '-day ' + destination + ' itinerary: ')}`;
            }

            showToast('Your itinerary is ready! 🎉', 'success');
        } else {
            outputContent.innerHTML = `<div class="p-4 text-danger">Failed to generate itinerary. Please try again.</div>`;
        }
    } catch (err) {
        console.error('[Planner] Error:', err);
        if (outputContent) {
            outputContent.innerHTML = `<div class="p-4 text-danger"><i class="bi bi-exclamation-triangle me-2"></i>Connection error. Please try again.</div>`;
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-robot me-2"></i>Generate My Itinerary with IBM Granite AI';
        }
    }
}

// ── Copy & Download Itinerary ─────────────────────────────────────────────────
function copyItinerary() {
    const content = document.getElementById('itineraryContent')?.innerText;
    if (content) copyToClipboard(content, '📋 Itinerary copied to clipboard!');
}

function downloadItinerary() {
    const content = document.getElementById('itineraryContent')?.innerText;
    const dest    = document.getElementById('planDestination')?.value || 'itinerary';
    if (!content) return;

    const blob = new Blob([`Atlas Travel Planner — Itinerary\n${'='.repeat(50)}\n\n${content}`], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `atlas-${dest.replace(/\s+/g, '-').toLowerCase()}-itinerary.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Itinerary downloaded!', 'success');
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
