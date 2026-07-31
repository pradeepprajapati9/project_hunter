/* project-hunter dashboard — leads.json padho, filter/sort karo, render karo */

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
  'video-audio': 'Video / audio / photo',
  'marketing-seo': 'Marketing / sales',
  'va-support': 'VA / support',
  'teaching': 'Teaching',
  'finance-legal': 'Finance / legal',
  'ecommerce': 'E-commerce',
  'field-trade': 'Field / trade',
};

/* auto-derived category ka naam bhi theek dikhe */
const catLabel = (c) => CAT_LABEL[c] || c.replace(/[-_]/g, ' ').replace(/^\w/, (m) => m.toUpperCase());

const CONTACT_LABEL = { email: 'email', telegram: 'telegram', form: 'apply form', discord: 'discord', dm: 'DM only' };

const DONE_KEY = 'ph:contacted';

const state = {
  leads: [],
  cat: 'all',
  q: '',
  sort: 'fresh',
  onlyBudget: false,
  hideDone: false,
  onlyRemote: false,
  hideShady: false,
  done: new Set(JSON.parse(localStorage.getItem(DONE_KEY) || '[]')),
};

const el = (id) => document.getElementById(id);

/* ---------- load ---------- */

async function load() {
  try {
    const res = await fetch('../data/leads.json?t=' + Date.now());
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    state.leads = data.leads || [];
    el('stamp').innerHTML = `updated <b>${timeAgo(data.generated_at)}</b> &middot; <b>+${data.new_this_run || 0}</b> is run me`;
    renderStats();
    renderChips();
    render();
  } catch (err) {
    showNotice('<b>leads.json nahi mila</b>Pehle scraper chalao: <code>python hunter.py</code>');
  }
}

/* ---------- stats ---------- */

function renderStats() {
  const leads = state.leads;
  const today = leads.filter((l) => hoursAgo(l.posted_at) < 24).length;
  const withBudget = leads.filter((l) => l.budget.stated).length;
  const direct = leads.filter((l) => ['email', 'telegram', 'form', 'discord'].includes(l.contact.kind)).length;

  const shady = leads.filter((l) => l.trust && l.trust.level === 'suspicious').length;

  const tiles = [
    { n: leads.length, label: 'live leads', cls: '' },
    { n: today, label: 'aaj ke', cls: 'accent' },
    { n: withBudget, label: 'budget likha hai', cls: 'money' },
    { n: direct, label: 'direct contact', cls: '' },
    { n: shady, label: 'shak wale', cls: 'warn' },
    { n: state.done.size, label: 'contacted', cls: '' },
  ];

  el('stats').innerHTML = tiles.map((t) => `
    <div class="stat ${t.cls}">
      <div class="stat-num">${t.n}</div>
      <div class="stat-label">${t.label}</div>
    </div>`).join('');
}

/* ---------- chips ---------- */

function renderChips() {
  const counts = {};
  state.leads.forEach((l) => { counts[l.category] = (counts[l.category] || 0) + 1; });

  const cats = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const chips = [`<button class="chip ${state.cat === 'all' ? 'on' : ''}" data-cat="all">All<span class="n">${state.leads.length}</span></button>`]
    .concat(cats.map((c) => `<button class="chip ${state.cat === c ? 'on' : ''}" data-cat="${esc(c)}">${esc(catLabel(c))}<span class="n">${counts[c]}</span></button>`));

  el('chips').innerHTML = chips.join('');
  el('chips').querySelectorAll('.chip').forEach((btn) => {
    btn.onclick = () => { state.cat = btn.dataset.cat; renderChips(); render(); };
  });
}

/* ---------- render ---------- */

function visible() {
  const q = state.q.toLowerCase().trim();
  let out = state.leads.filter((l) => {
    if (state.cat !== 'all' && l.category !== state.cat) return false;
    if (state.onlyBudget && !l.budget.stated) return false;
    if (state.hideDone && state.done.has(l.id)) return false;
    if (state.onlyRemote && (l.flags || []).includes('onsite')) return false;
    if (state.hideShady && l.trust && l.trust.level !== 'clean') return false;
    if (q && !(`${l.title} ${l.body} ${l.source_detail}`.toLowerCase().includes(q))) return false;
    return true;
  });

  const cmp = {
    fresh: (a, b) => (b.posted_at || '').localeCompare(a.posted_at || ''),
    score: (a, b) => (b.score || 0) - (a.score || 0) || (b.posted_at || '').localeCompare(a.posted_at || ''),
    budget: (a, b) => (b.budget.stated - a.budget.stated) || (b.score || 0) - (a.score || 0),
  }[state.sort];

  return out.sort(cmp);
}

function render() {
  const leads = visible();
  const grid = el('grid');

  if (!leads.length) {
    grid.innerHTML = '';
    showNotice('<b>Kuch nahi mila</b>Filter hatao ya scraper dubara chalao.');
    return;
  }
  el('notice').hidden = true;
  grid.innerHTML = leads.map(card).join('');

  grid.querySelectorAll('[data-done]').forEach((btn) => {
    btn.onclick = () => toggleDone(btn.dataset.done);
  });
  grid.querySelectorAll('.snippet').forEach((p) => {
    p.onclick = () => p.closest('.card').classList.toggle('open');
  });
}

function card(l) {
  const isDone = state.done.has(l.id);
  const hot = (l.score || 0) >= 60;
  const budget = l.budget.stated
    ? `<span class="tag money">${esc(l.budget.raw)}${l.budget.hourly ? '/hr' : ''}</span>`
    : '';
  const flags = (l.flags || []).map((f) => `<span class="tag ${f === 'urgent' ? 'urgent' : ''}">${f}</span>`).join('');
  const trust = l.trust && l.trust.level === 'suspicious'
    ? `<span class="tag warn" title="${esc((l.trust.reasons || []).join(' • '))}">⚠ dhyan se</span>`
    : '';
  const contact = l.contact.kind
    ? `<span class="contact" title="${esc(l.contact.value)}">${CONTACT_LABEL[l.contact.kind] || l.contact.kind}</span>`
    : '';

  return `
  <article class="card ${isDone ? 'done' : ''}">
    <div class="card-top">
      <div class="score ${hot ? 'hot' : ''}" title="lead score ${l.score || 0}/100">${l.score || 0}</div>
      <div>
        <h3><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.title)}</a></h3>
        <div class="meta">
          <span>${esc(l.source)}</span><span class="dot">•</span>
          <span>${esc(l.source_detail)}</span><span class="dot">•</span>
          <span>${timeAgo(l.posted_at)}</span>
          ${l.author ? `<span class="dot">•</span><span>${esc(l.author)}</span>` : ''}
        </div>
      </div>
    </div>

    <div class="tags">
      <span class="tag cat ${l.category_auto ? 'auto' : ''}" title="${l.category_auto ? 'auto-detected — pakka nahi' : 'keyword match'}">${esc(catLabel(l.category))}</span>
      ${l.category_auto && l.topic ? `<span class="tag">${esc(l.topic)}</span>` : ''}
      ${budget}${trust}${flags}
    </div>

    <p class="snippet" title="click to expand">${esc(l.body)}</p>

    <div class="card-foot">
      <a class="btn primary" href="${esc(l.url)}" target="_blank" rel="noopener">Kholo</a>
      <button class="btn ghost ${isDone ? 'on' : ''}" data-done="${l.id}">${isDone ? '✓ contacted' : 'mark contacted'}</button>
      ${contact}
    </div>
  </article>`;
}

function toggleDone(id) {
  state.done.has(id) ? state.done.delete(id) : state.done.add(id);
  localStorage.setItem(DONE_KEY, JSON.stringify([...state.done]));
  renderStats();
  render();
}

/* ---------- helpers ---------- */

function showNotice(html) {
  const n = el('notice');
  n.innerHTML = html;
  n.hidden = false;
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

/* ---------- events ---------- */

el('q').oninput = (e) => { state.q = e.target.value; render(); };
el('sort').onchange = (e) => { state.sort = e.target.value; render(); };
el('onlyBudget').onchange = (e) => { state.onlyBudget = e.target.checked; render(); };
el('onlyRemote').onchange = (e) => { state.onlyRemote = e.target.checked; render(); };
el('hideShady').onchange = (e) => { state.hideShady = e.target.checked; render(); };
el('hideDone').onchange = (e) => { state.hideDone = e.target.checked; render(); };

load();
