/* project-hunter dashboard — Bootstrap only, no custom CSS */

const CAT_LABEL = {
  'web-dev': 'Web dev',
  'mobile-app': 'Mobile app',
  'automation-bot': 'Automation / bot',
  'ai-ml': 'AI / ML',
  'software-eng': 'Software / DevOps',
  'data': 'Data',
  'design': 'Design',
  'writing': 'Writing',
  'translation': 'Translation',
  'video-audio': 'Video / audio',
  'marketing-seo': 'Marketing / sales',
  'va-support': 'VA / support',
  'teaching': 'Teaching',
  'finance-legal': 'Finance / legal',
  'ecommerce': 'E-commerce',
  'field-trade': 'Field / trade',
  'odd-jobs': 'Odd jobs',
  'other': 'Other',
};

const CONTACT_LABEL = {
  email: 'Email address in post',
  telegram: 'Telegram',
  form: 'Application form',
  discord: 'Discord',
  dm: 'Direct message',
};

const DONE_KEY = 'ph:contacted';
const THEME_KEY = 'ph:theme';
const SNIPPET = 150;

const catLabel = (c) => CAT_LABEL[c] || c.replace(/[-_]/g, ' ').replace(/^\w/, (m) => m.toUpperCase());
const el = (id) => document.getElementById(id);

const state = {
  leads: [],
  cat: 'all',
  q: '',
  sort: 'fresh',
  onlyBudget: false,
  onlyRemote: false,
  hideShady: false,
  hideDone: false,
  done: new Set(JSON.parse(localStorage.getItem(DONE_KEY) || '[]')),
};

/* ---------- load ---------- */

/* Locally the full file is used; on GitHub Pages only the sanitised copy exists. */
async function fetchLeads() {
  for (const path of ['../data/leads.json', 'data/leads.json']) {
    try {
      const res = await fetch(path + '?t=' + Date.now());
      if (res.ok) return await res.json();
    } catch (err) { /* try the next path */ }
  }
  return null;
}

async function load() {
  try {
    const data = await fetchLeads();
    if (!data) throw new Error('no data');
    state.leads = data.leads || [];
    el('stamp').textContent = `updated ${timeAgo(data.generated_at)} · ${data.new_this_run || 0} new`;
    el('navCount').textContent = state.leads.length;
    renderStats();
    fillCategories();
    render();
  } catch (err) {
    notice('No leads file found — run <code>python hunter.py</code> first.');
  }
}

/* ---------- stats ---------- */

function renderStats() {
  const leads = state.leads;
  const tiles = [
    { n: leads.length, label: 'Live leads', color: 'text-body' },
    { n: leads.filter((l) => hoursAgo(l.posted_at) < 24).length, label: 'Posted today', color: 'text-primary' },
    { n: leads.filter((l) => l.budget.stated).length, label: 'Budget stated', color: 'text-success' },
    { n: state.done.size, label: 'Contacted', color: 'text-body-secondary' },
  ];

  el('stats').innerHTML = tiles.map((t) => `
    <div class="col-6 col-lg-3">
      <div class="card h-100">
        <div class="card-body py-3">
          <div class="fs-3 fw-semibold ${t.color}">${t.n}</div>
          <div class="small text-body-secondary">${t.label}</div>
        </div>
      </div>
    </div>`).join('');
}

/* ---------- category dropdown ---------- */

function fillCategories() {
  const counts = {};
  state.leads.forEach((l) => { counts[l.category] = (counts[l.category] || 0) + 1; });

  const opts = Object.keys(counts)
    .sort((a, b) => counts[b] - counts[a])
    .map((c) => `<option value="${esc(c)}">${esc(catLabel(c))} (${counts[c]})</option>`);

  el('cat').innerHTML = `<option value="all">All categories (${state.leads.length})</option>` + opts.join('');
}

/* ---------- filter + sort ---------- */

function visible() {
  const q = state.q.toLowerCase().trim();
  const out = state.leads.filter((l) => {
    if (state.cat !== 'all' && l.category !== state.cat) return false;
    if (state.onlyBudget && !l.budget.stated) return false;
    if (state.onlyRemote && (l.flags || []).includes('onsite')) return false;
    if (state.hideShady && l.trust && l.trust.level !== 'clean') return false;
    if (state.hideDone && state.done.has(l.id)) return false;
    if (q && !`${l.title} ${l.body} ${l.source_detail}`.toLowerCase().includes(q)) return false;
    return true;
  });

  const cmp = {
    fresh: (a, b) => (b.posted_at || '').localeCompare(a.posted_at || ''),
    score: (a, b) => (b.score || 0) - (a.score || 0) || (b.posted_at || '').localeCompare(a.posted_at || ''),
    budget: (a, b) => (b.budget.stated - a.budget.stated) || (b.score || 0) - (a.score || 0),
  }[state.sort];

  return out.sort(cmp);
}

/* ---------- render ---------- */

function render() {
  const leads = visible();
  const grid = el('grid');

  if (!leads.length) {
    grid.innerHTML = '';
    notice('Nothing matches these filters.');
    return;
  }
  el('notice').classList.add('d-none');
  grid.innerHTML = leads.map(card).join('');

  grid.querySelectorAll('[data-done]').forEach((b) => { b.onclick = () => toggleDone(b.dataset.done); });
  grid.querySelectorAll('[data-open]').forEach((b) => { b.onclick = () => openLead(b.dataset.open); });
}

function badges(l) {
  const out = [`<span class="badge text-bg-secondary">${esc(catLabel(l.category))}</span>`];

  if (l.budget.stated) {
    out.push(`<span class="badge text-bg-success">${esc(l.budget.raw)}${l.budget.hourly ? '/hr' : ''}</span>`);
  }
  if (l.trust && l.trust.level === 'suspicious') {
    out.push(`<span class="badge text-bg-danger" title="${esc((l.trust.reasons || []).join(' • '))}">⚠ check carefully</span>`);
  }
  (l.flags || []).forEach((f) => {
    const tone = f === 'urgent' ? 'text-bg-warning' : 'text-bg-light';
    out.push(`<span class="badge ${tone}">${esc(f)}</span>`);
  });
  return out.join(' ');
}

function card(l) {
  const done = state.done.has(l.id);
  const tone = (l.score || 0) >= 70 ? 'text-bg-primary' : 'text-bg-secondary';

  return `
  <div class="col">
    <div class="card h-100 ${done ? 'opacity-50' : ''}">
      <div class="card-body d-flex flex-column">

        <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
          <h6 class="card-title mb-0 lh-base">${esc(l.title)}</h6>
          <span class="badge ${tone} flex-shrink-0" title="lead score ${l.score || 0}/100">${l.score || 0}</span>
        </div>

        <p class="card-subtitle small text-body-secondary mb-2">
          ${esc(l.source_detail)} · ${timeAgo(l.posted_at)}${l.author ? ' · ' + esc(l.author) : ''}
        </p>

        <div class="d-flex flex-wrap gap-1 mb-3">${badges(l)}</div>

        <p class="card-text small text-body-secondary">${esc(snippet(l.body))}</p>

        <div class="d-flex gap-2 mt-auto pt-2">
          <button class="btn btn-sm btn-primary" data-open="${l.id}">Details</button>
          <a class="btn btn-sm btn-outline-secondary" href="${esc(l.url)}" target="_blank" rel="noopener">Post</a>
          <button class="btn btn-sm ${done ? 'btn-success' : 'btn-outline-success'} ms-auto" data-done="${l.id}">
            ${done ? '✓ contacted' : 'Contacted'}
          </button>
        </div>

      </div>
    </div>
  </div>`;
}

/* ---------- detail modal ---------- */

const modal = new bootstrap.Modal('#leadModal');

function openLead(id) {
  const l = state.leads.find((x) => x.id === id);
  if (!l) return;

  el('modalTitle').textContent = l.title;
  el('modalTags').innerHTML = badges(l);
  el('modalBody').innerHTML = (l.body || '(no details in the post)')
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => `<p class="mb-2">${esc(line)}</p>`)
    .join('');
  el('modalContact').textContent = l.contact.kind
    ? `${CONTACT_LABEL[l.contact.kind] || l.contact.kind}${l.contact.value ? ': ' + l.contact.value : ''}`
    : 'Contact details are in the post';
  el('modalLink').href = l.url;
  modal.show();
}

/* ---------- actions ---------- */

function toggleDone(id) {
  state.done.has(id) ? state.done.delete(id) : state.done.add(id);
  localStorage.setItem(DONE_KEY, JSON.stringify([...state.done]));
  renderStats();
  render();
}

function notice(html) {
  const n = el('notice');
  n.innerHTML = html;
  n.classList.remove('d-none');
}

/* ---------- helpers ---------- */

function snippet(text) {
  const clean = (text || '').replace(/\s+/g, ' ').trim();
  return clean.length > SNIPPET ? clean.slice(0, SNIPPET).trimEnd() + '…' : clean;
}

function hoursAgo(iso) {
  const t = Date.parse(iso || '');
  return isNaN(t) ? 1e9 : (Date.now() - t) / 3.6e6;
}

function timeAgo(iso) {
  const h = hoursAgo(iso);
  if (h > 1e8) return '—';
  if (h < 1) return Math.max(1, Math.round(h * 60)) + 'm ago';
  if (h < 24) return Math.round(h) + 'h ago';
  const d = Math.round(h / 24);
  return d + (d === 1 ? ' day ago' : ' days ago');
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ---------- theme ---------- */

function setTheme(mode) {
  document.documentElement.setAttribute('data-bs-theme', mode);
  el('themeBtn').textContent = mode === 'dark' ? 'Light' : 'Dark';
  localStorage.setItem(THEME_KEY, mode);
}

setTheme(localStorage.getItem(THEME_KEY) || 'dark');
el('themeBtn').onclick = () =>
  setTheme(document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');

/* ---------- events ---------- */

el('q').oninput = (e) => { state.q = e.target.value; render(); };
el('cat').onchange = (e) => { state.cat = e.target.value; render(); };
el('sort').onchange = (e) => { state.sort = e.target.value; render(); };
el('onlyBudget').onchange = (e) => { state.onlyBudget = e.target.checked; render(); };
el('onlyRemote').onchange = (e) => { state.onlyRemote = e.target.checked; render(); };
el('hideShady').onchange = (e) => { state.hideShady = e.target.checked; render(); };
el('hideDone').onchange = (e) => { state.hideDone = e.target.checked; render(); };

load();
