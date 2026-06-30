'use strict';

const viewEl = document.getElementById('view');
const titleEl = document.getElementById('page-title');
const kickerEl = document.getElementById('page-kicker');
const modalBackdrop = document.getElementById('modal-backdrop');
const modalEl = document.getElementById('modal');
const toastStack = document.getElementById('toast-stack');
const sidebar = document.getElementById('sidebar');

const state = {
  view: 'dashboard',
  meta: null,
  facets: null,
  programmes: null,
  pendingImportFile: null,
  assets: {
    offset: 0,
    limit: 20,
    q: '',
    site: '',
    asset_type: '',
    support_status: '',
    risk_band: '',
    programme_id: '',
    sort_by: 'risk_score',
    sort_dir: 'desc',
  },
};

const pageMeta = {
  dashboard: ['Portfolio dashboard', 'Portfolio intelligence'],
  assets: ['Asset register', 'Evidence and risk'],
  programmes: ['Programme packages', 'Investment and delivery'],
  data: ['Data exchange', 'Controlled migration'],
};

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function classToken(value) {
  return String(value ?? '').replaceAll(' ', '-').replaceAll('_', '-').replace(/[^a-zA-Z0-9-]/g, '');
}

function label(value) {
  if (value === null || value === undefined || value === '') return 'Not set';
  return String(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value) {
  if (!value) return 'Not set';
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.valueOf()) ? esc(value) : new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
}

function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? '' : new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(date);
}

function formatMoney(value, compact = true) {
  const amount = Number(value || 0);
  if (compact && Math.abs(amount) >= 1_000_000) return `£${(amount / 1_000_000).toFixed(2)}m`;
  if (compact && Math.abs(amount) >= 1_000) return `£${Math.round(amount / 1_000)}k`;
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(amount);
}

function badge(value) {
  return `<span class="badge ${classToken(value)}">${esc(label(value))}</span>`;
}

function score(scoreValue, band) {
  return `<span class="score"><span class="score-ring dot-${classToken(band)}"></span>${Number(scoreValue).toFixed(1)}</span>`;
}

function options(items, selected, placeholder = null) {
  const first = placeholder === null ? '' : `<option value="">${esc(placeholder)}</option>`;
  return first + items.map((item) => {
    const value = typeof item === 'object' ? item.value : item;
    const text = typeof item === 'object' ? item.label : label(item);
    return `<option value="${esc(value)}" ${String(value) === String(selected ?? '') ? 'selected' : ''}>${esc(text)}</option>`;
  }).join('');
}

function ratingOptions(selected) {
  const ratings = [
    { value: 1, label: '1 · Low' },
    { value: 2, label: '2 · Low–moderate' },
    { value: 3, label: '3 · Moderate' },
    { value: 4, label: '4 · High' },
    { value: 5, label: '5 · Severe' },
  ];
  return options(ratings, selected);
}

async function api(path, options = {}) {
  const config = { ...options, headers: { ...(options.headers || {}) } };
  if (config.body && !(config.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(path, config);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) {
        detail = body.detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
      } else if (body.detail) {
        detail = body.detail;
      } else if (body.message) {
        detail = body.message;
      }
    } catch (_) {
      // Preserve status text.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
}

function toast(title, message = '', type = 'success') {
  const item = document.createElement('div');
  item.className = `toast ${type}`;
  item.innerHTML = `<div>${type === 'error' ? '!' : '✓'}</div><div><strong>${esc(title)}</strong>${message ? `<span>${esc(message)}</span>` : ''}</div>`;
  toastStack.appendChild(item);
  window.setTimeout(() => item.remove(), 4600);
}

function setLoading(message = 'Loading live data…') {
  viewEl.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>${esc(message)}</p></div>`;
}

function setPage(viewName) {
  const [title, kicker] = pageMeta[viewName] || pageMeta.dashboard;
  titleEl.textContent = title;
  kickerEl.textContent = kicker;
  document.querySelectorAll('[data-nav]').forEach((button) => button.classList.toggle('active', button.dataset.nav === viewName));
}

async function loadMeta() {
  if (!state.meta) state.meta = await api('/api/meta');
  return state.meta;
}

async function loadFacets(force = false) {
  if (!state.facets || force) state.facets = await api('/api/assets/facets');
  return state.facets;
}

async function loadProgrammes(force = false) {
  if (!state.programmes || force) state.programmes = await api('/api/programmes');
  return state.programmes;
}

function metricCard(labelText, value, foot, icon, flavour = '') {
  return `<article class="metric-card ${flavour}">
    <div class="metric-label"><span>${esc(labelText)}</span><span class="metric-icon">${esc(icon)}</span></div>
    <div class="metric-value">${esc(value)}</div>
    <div class="metric-foot">${esc(foot)}</div>
  </article>`;
}

function distributionRows(items) {
  const maximum = Math.max(1, ...items.map((item) => item.count));
  return items.map((item) => `<div class="distribution-row">
    <div class="distribution-label"><span class="distribution-dot dot-${classToken(item.name)}"></span>${esc(label(item.name))}</div>
    <div class="distribution-track"><div class="distribution-fill fill-${classToken(item.name)}" style="width:${Math.max(2, item.count / maximum * 100)}%"></div></div>
    <div class="distribution-count">${item.count}</div>
  </div>`).join('');
}

async function renderDashboard() {
  setLoading('Building the portfolio view…');
  const [data, meta] = await Promise.all([api('/api/dashboard/summary'), loadMeta()]);
  const m = data.metrics;
  const demoCallout = meta.demo_seed_enabled ? `<div class="callout">
    <div class="callout-icon">i</div>
    <div><strong>Fictional demonstration portfolio</strong><p>The supplied records are examples. Import your controlled register or disable SEED_DEMO before deployment.</p></div>
  </div>` : '';

  const topRows = data.top_assets.length ? data.top_assets.map((asset) => `<tr class="clickable" data-action="edit-asset" data-id="${asset.id}">
    <td><span class="code">${esc(asset.asset_code)}</span><span class="cell-secondary">${esc(asset.site)}</span></td>
    <td><span class="cell-primary">${esc(asset.system_name)}</span><span class="cell-secondary">${esc(label(asset.support_status))}</span></td>
    <td>${score(asset.risk_score, asset.risk_band)}</td>
    <td>${badge(asset.risk_band)}</td>
    <td>${badge(asset.recommended_wave)}</td>
  </tr>`).join('') : `<tr><td colspan="5"><div class="empty-state"><strong>No assets yet</strong>Import or create the first asset record.</div></td></tr>`;

  const siteRows = data.sites.map((site) => `<tr>
    <td><span class="cell-primary">${esc(site.site)}</span></td>
    <td>${site.assets}</td><td>${site.high_risk}</td><td>${score(site.average_risk, site.average_risk >= 60 ? 'High' : site.average_risk >= 40 ? 'Medium' : 'Low')}</td>
  </tr>`).join('') || `<tr><td colspan="4">No site data</td></tr>`;

  const activity = data.recent_activity.map((event) => `<div class="activity-item">
    <div class="activity-icon">${esc(event.action.slice(0, 1).toUpperCase())}</div>
    <div class="activity-text"><strong>${esc(event.summary)}</strong><span>${esc(label(event.entity_type))} · ${esc(event.actor)}</span></div>
    <div class="activity-time">${esc(formatDateTime(event.created_at))}</div>
  </div>`).join('') || '<div class="empty-state"><span>No activity recorded.</span></div>';

  viewEl.innerHTML = `
    <div class="page-intro">
      <div><h2>Portfolio exposure at a glance</h2><p>Risk, lifecycle evidence and delivery readiness are calculated from the live register, then rolled into intervention packages.</p></div>
      <div class="page-actions"><button class="button secondary" data-action="refresh-dashboard">↻ Refresh</button><button class="button primary" data-action="new-asset">＋ Add asset</button></div>
    </div>
    ${demoCallout}
    <section class="metric-grid">
      ${metricCard('Registered assets', m.total_assets, `${m.data_completeness}% average data completeness`, '▦')}
      ${metricCard('High / critical', m.high_risk_assets, `${m.average_risk} portfolio average risk`, '▲', 'risk')}
      ${metricCard('Unsupported', m.unsupported_assets, `${m.unknown_lifecycle} with unknown lifecycle`, '⌛', 'warning')}
      ${metricCard('Forecast funding', formatMoney(m.funding_estimate), `${m.active_programmes} active programme packages`, '£', 'money')}
    </section>

    <section class="content-grid">
      <article class="panel">
        <div class="panel-header"><div><h3>Risk distribution</h3><p>Calculated 0–100 using consequence, supportability and recovery exposure</p></div><button class="button ghost small" data-nav="assets">Open register →</button></div>
        <div class="panel-body"><div class="distribution">${distributionRows(data.risk_bands)}</div></div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h3>Evidence quality</h3><p>Unknowns are visible work, not quiet low risk</p></div>${badge(`${data.data_quality.average_completeness}% complete`)}</div>
        <div class="panel-body">
          <div class="quality-grid">
            <div class="quality-card"><strong>${data.data_quality.low_confidence}</strong><span>Low-confidence records</span></div>
            <div class="quality-card"><strong>${data.data_quality.missing_owner}</strong><span>Missing accountable owner</span></div>
            <div class="quality-card"><strong>${data.data_quality.missing_support_date}</strong><span>Missing support date</span></div>
            <div class="quality-card"><strong>${data.data_quality.unassigned_programme}</strong><span>Unassigned to package</span></div>
          </div>
          <div class="progress"><span style="width:${data.data_quality.average_completeness}%"></span></div>
        </div>
      </article>
    </section>

    <article class="panel" style="margin-bottom:16px">
      <div class="panel-header"><div><h3>Highest current exposures</h3><p>Click a row to inspect evidence and treatment</p></div></div>
      <div class="panel-body flush"><div class="data-table-wrap"><table class="data-table"><thead><tr><th>Asset</th><th>System</th><th>Score</th><th>Band</th><th>Response</th></tr></thead><tbody>${topRows}</tbody></table></div></div>
    </article>

    <section class="content-grid equal">
      <article class="panel"><div class="panel-header"><div><h3>Site exposure</h3><p>Prioritised by average risk</p></div></div><div class="panel-body flush"><div class="data-table-wrap"><table class="data-table"><thead><tr><th>Site</th><th>Assets</th><th>High risk</th><th>Average</th></tr></thead><tbody>${siteRows}</tbody></table></div></div></article>
      <article class="panel"><div class="panel-header"><div><h3>Recent activity</h3><p>Database changes and imports</p></div></div><div class="panel-body"><div class="activity-list">${activity}</div></div></article>
    </section>`;
}

function buildAssetParams() {
  const params = new URLSearchParams();
  Object.entries(state.assets).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) params.set(key, value);
  });
  return params;
}

async function renderAssets() {
  setLoading('Loading the asset register…');
  const facets = await loadFacets();
  const data = await api(`/api/assets?${buildAssetParams().toString()}`);
  const pMap = new Map(facets.programmes.map((item) => [String(item.id), item.package_code]));
  const start = data.total ? data.offset + 1 : 0;
  const end = Math.min(data.offset + data.limit, data.total);

  const rows = data.items.map((asset) => `<tr class="clickable" data-action="edit-asset" data-id="${asset.id}">
    <td><span class="code">${esc(asset.asset_code)}</span><span class="cell-secondary">${esc(asset.asset_type)}</span></td>
    <td><span class="cell-primary">${esc(asset.system_name)}</span><span class="cell-secondary">${esc(asset.manufacturer || 'Manufacturer not captured')} ${esc(asset.model || '')}</span></td>
    <td><span class="cell-primary">${esc(asset.site)}</span><span class="cell-secondary">${esc(asset.process_area || 'Area not captured')}</span></td>
    <td>${badge(asset.support_status)}<span class="cell-secondary">${formatDate(asset.support_end_date)}</span></td>
    <td>${score(asset.risk_score, asset.risk_band)}<span class="cell-secondary">${esc(asset.risk_band)}</span></td>
    <td>${badge(asset.recommended_wave)}</td>
    <td><span class="cell-primary">${esc(pMap.get(String(asset.programme_id)) || 'Unassigned')}</span><span class="cell-secondary">${esc(asset.owner || 'No owner')}</span></td>
  </tr>`).join('');

  const body = rows || `<tr><td colspan="7"><div class="empty-state"><div class="empty-symbol">⌕</div><div><strong>No records match</strong>Adjust the filters or create a new asset.</div></div></td></tr>`;
  const hasPrev = state.assets.offset > 0;
  const hasNext = state.assets.offset + state.assets.limit < data.total;

  viewEl.innerHTML = `
    <div class="page-intro">
      <div><h2>Validated system and asset baseline</h2><p>Search, filter and update the live register. Every change recalculates exposure, recommended wave and data completeness.</p></div>
      <div class="page-actions"><a class="button secondary" href="/api/assets/export.csv">⇩ Export CSV</a><button class="button primary" data-action="new-asset">＋ Add asset</button></div>
    </div>
    <form class="toolbar" id="asset-filters">
      <label class="toolbar-search"><span>⌕</span><input type="search" name="q" value="${esc(state.assets.q)}" placeholder="Asset code, system, vendor or owner"></label>
      <select class="select" name="site" data-filter>${options(facets.sites, state.assets.site, 'All sites')}</select>
      <select class="select" name="support_status" data-filter>${options(facets.support_statuses, state.assets.support_status, 'All lifecycle states')}</select>
      <select class="select" name="risk_band" data-filter>${options(facets.risk_bands, state.assets.risk_band, 'All risk bands')}</select>
      <select class="select" name="programme_id" data-filter>${options(facets.programmes.map((p) => ({ value: p.id, label: p.package_code })), state.assets.programme_id, 'All packages')}</select>
      <select class="select" name="sort_by" data-filter>${options([
        { value: 'risk_score', label: 'Sort: risk score' }, { value: 'asset_code', label: 'Sort: asset code' }, { value: 'site', label: 'Sort: site' }, { value: 'updated_at', label: 'Sort: updated' },
      ], state.assets.sort_by)}</select>
      <button class="button secondary small" type="button" data-action="clear-asset-filters">Clear</button>
    </form>
    <article class="panel">
      <div class="panel-body flush"><div class="data-table-wrap"><table class="data-table"><thead><tr><th>Asset</th><th>System</th><th>Location</th><th>Lifecycle</th><th>Risk</th><th>Response</th><th>Package / owner</th></tr></thead><tbody>${body}</tbody></table></div></div>
      <div class="table-meta"><span>Showing ${start}–${end} of ${data.total} live records</span><div class="pagination"><button class="button secondary small" data-action="asset-prev" ${hasPrev ? '' : 'disabled'}>← Previous</button><button class="button secondary small" data-action="asset-next" ${hasNext ? '' : 'disabled'}>Next →</button></div></div>
    </article>`;
}

async function renderProgrammes() {
  setLoading('Loading intervention packages…');
  const programmes = await loadProgrammes(true);
  const totalBudget = programmes.reduce((sum, item) => sum + Number(item.total_budget || 0), 0);
  const totalAssets = programmes.reduce((sum, item) => sum + item.asset_count, 0);
  const criticalAssets = programmes.reduce((sum, item) => sum + item.critical_assets, 0);
  const deliveryCount = programmes.filter((item) => ['ready', 'delivery', 'acceptance'].includes(item.status)).length;

  const cards = programmes.map((programme) => `<article class="programme-card" data-action="edit-programme" data-id="${programme.id}">
    <div class="programme-top"><span class="programme-code">${esc(programme.package_code)}</span>${badge(programme.target_wave)}</div>
    <h3>${esc(programme.title)}</h3>
    <p>${esc(programme.description || 'No problem statement has been recorded.')}</p>
    <div class="programme-stats">
      <div class="programme-stat"><strong>${programme.asset_count}</strong><span>Linked assets</span></div>
      <div class="programme-stat"><strong>${programme.average_risk.toFixed(1)}</strong><span>Average risk</span></div>
      <div class="programme-stat"><strong>${formatMoney(programme.total_budget)}</strong><span>Incl. contingency</span></div>
    </div>
    <div class="programme-footer"><span>${badge(programme.status)}</span><span>${esc(programme.owner || 'Owner not set')}</span></div>
  </article>`).join('') || `<div class="empty-state"><div class="empty-symbol">◇</div><div><strong>No programme packages</strong>Create the first intervention package.</div></div>`;

  viewEl.innerHTML = `
    <div class="page-intro">
      <div><h2>From ageing assets to investable work</h2><p>Packages combine related risks into governed scopes with ownership, funding, dependencies, outage windows and delivery gates.</p></div>
      <div class="page-actions"><button class="button primary" data-action="new-programme">＋ New package</button></div>
    </div>
    <section class="metric-grid">
      ${metricCard('Programme packages', programmes.length, `${deliveryCount} at ready / delivery stages`, '◇')}
      ${metricCard('Linked assets', totalAssets, `${criticalAssets} critical assets inside packages`, '▦', 'risk')}
      ${metricCard('Funding envelope', formatMoney(totalBudget), 'Includes package contingency', '£', 'money')}
      ${metricCard('Unassigned assets', Math.max(0, (await api('/api/dashboard/summary')).data_quality.unassigned_programme), 'Need packaging or an explicit monitor decision', '↗', 'warning')}
    </section>
    <section class="programme-grid">${cards}</section>`;
}

async function renderData() {
  setLoading('Preparing data controls…');
  const [summary, meta] = await Promise.all([api('/api/dashboard/summary'), loadMeta()]);
  const q = summary.data_quality;
  viewEl.innerHTML = `
    <div class="page-intro">
      <div><h2>Move the register without losing control</h2><p>Import existing CSV data into normalized records, upsert by asset code, and export the current database whenever an offline handoff is required.</p></div>
      <div class="page-actions"><a class="button secondary" href="/api/assets/export.csv">⇩ Export current register</a></div>
    </div>
    <div class="callout"><div class="callout-icon">!</div><div><strong>Use a controlled transfer route</strong><p>This application is for lifecycle planning. Do not connect it directly to production SCADA or permit active discovery from the application tier.</p></div></div>
    <section class="content-grid">
      <article class="panel">
        <div class="panel-header"><div><h3>CSV import</h3><p>Existing asset_code values are updated; new codes are created</p></div><a class="button ghost small" href="/static/sample-import.csv">Sample template ↓</a></div>
        <div class="panel-body">
          <form id="import-form">
            <div class="upload-zone" id="upload-zone">
              <div class="upload-symbol">⇧</div>
              <h3 id="upload-title">Drop a UTF-8 CSV here</h3>
              <p id="upload-file-name">or select a file from a controlled workspace</p>
              <input type="file" id="import-file" accept=".csv,text/csv" hidden>
              <button class="button secondary" type="button" data-action="select-import-file">Choose CSV</button>
              <button class="button primary" type="submit">Import into database</button>
            </div>
          </form>
          <div id="import-result" class="import-result"></div>
        </div>
        <div class="panel-footer">The importer validates 1–5 ratings, lifecycle values and programme references. Computed risk fields are ignored and recalculated.</div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h3>Current data quality</h3><p>${summary.metrics.total_assets} records in the relational database</p></div>${badge(`${q.average_completeness}% complete`)}</div>
        <div class="panel-body">
          <div class="quality-grid">
            <div class="quality-card"><strong>${q.low_confidence}</strong><span>Confidence C or D</span></div>
            <div class="quality-card"><strong>${q.missing_owner}</strong><span>Missing owner</span></div>
            <div class="quality-card"><strong>${q.missing_support_date}</strong><span>Missing support date</span></div>
            <div class="quality-card"><strong>${q.unassigned_programme}</strong><span>Unassigned package</span></div>
          </div>
          <div class="progress"><span style="width:${q.average_completeness}%"></span></div>
        </div>
        <div class="panel-footer">Database source: ${esc(meta.data_source)} · Application ${esc(meta.version)}</div>
      </article>
    </section>
    <section class="content-grid equal">
      <article class="panel"><div class="panel-header"><div><h3>Required minimum columns</h3><p>For creation</p></div></div><div class="panel-body"><p><span class="code">asset_code</span>, <span class="code">system_name</span> and <span class="code">site</span>. All other fields have controlled defaults, but incomplete evidence remains visible in the quality score.</p></div></article>
      <article class="panel"><div class="panel-header"><div><h3>Production database path</h3><p>Scale without redesigning the API</p></div></div><div class="panel-body"><p>Set <span class="code">DATABASE_URL</span> to a managed PostgreSQL service, run schema migrations, place the application behind enterprise SSO and retain database backups and audit logs.</p></div></article>
    </section>`;
  bindUploadZone();
}

function openModal(html, compact = false) {
  modalEl.className = compact ? 'modal compact' : 'modal';
  modalEl.innerHTML = html;
  modalBackdrop.hidden = false;
  document.body.style.overflow = 'hidden';
  const first = modalEl.querySelector('input, select, textarea, button');
  if (first) window.setTimeout(() => first.focus(), 0);
}

function closeModal() {
  modalBackdrop.hidden = true;
  modalEl.innerHTML = '';
  document.body.style.overflow = '';
}

async function openAssetModal(id = null) {
  const facets = await loadFacets();
  const asset = id ? await api(`/api/assets/${id}`) : {
    asset_code: '', system_name: '', site: '', process_area: '', asset_type: 'Other', manufacturer: '', model: '', software_version: '', firmware_version: '', os_version: '',
    support_status: 'unknown', support_end_date: '', business_criticality: 3, safety_impact: 3, production_impact: 3, cyber_exposure: 3, failure_likelihood: 3,
    spares_risk: 3, recoverability_risk: 3, dependency_complexity: 3, evidence_confidence: 'D', delivery_readiness: 1, treatment: 'assess', owner: '', notes: '', programme_id: '',
  };
  const assetTypes = Array.from(new Set([...facets.asset_types, 'SCADA Server', 'Operator Workstation', 'Engineering Workstation', 'PLC', 'RTU', 'Historian', 'Network Switch', 'Protocol Gateway', 'Communications', 'Remote Access', 'Other'])).sort();
  const headerText = id ? `${asset.asset_code} · ${asset.system_name}` : 'Create a controlled asset record';
  const scorePreview = id ? `<div class="score-preview"><div class="score-preview-value">${asset.risk_score.toFixed(1)}</div><div><strong>${badge(asset.risk_band)} ${badge(asset.recommended_wave)}</strong><p>${asset.data_completeness}% data completeness. Saving recalculates all three values.</p></div></div>` : `<div class="score-preview"><div class="score-preview-value">New</div><div><strong>Assessment calculated on save</strong><p>Unknown lifecycle and low evidence confidence deliberately increase exposure.</p></div></div>`;

  openModal(`<form id="asset-form" data-id="${id || ''}">
    <div class="modal-header"><div><h2 id="modal-title">${id ? 'Edit asset assessment' : 'Add asset'}</h2><p>${esc(headerText)}</p></div><button class="icon-button" type="button" data-action="close-modal" aria-label="Close">×</button></div>
    <div class="modal-body">
      ${scorePreview}
      <section class="form-section"><div class="form-section-title">Identity and accountability</div><div class="form-grid">
        <div class="field"><label>Asset code <span class="required">*</span></label><input class="input" name="asset_code" required maxlength="80" value="${esc(asset.asset_code)}"></div>
        <div class="field span-2"><label>System name <span class="required">*</span></label><input class="input" name="system_name" required maxlength="200" value="${esc(asset.system_name)}"></div>
        <div class="field"><label>Site <span class="required">*</span></label><input class="input" name="site" required list="site-list" value="${esc(asset.site)}"><datalist id="site-list">${facets.sites.map((site) => `<option value="${esc(site)}">`).join('')}</datalist></div>
        <div class="field"><label>Process area</label><input class="input" name="process_area" value="${esc(asset.process_area || '')}"></div>
        <div class="field"><label>Asset type</label><select class="input" name="asset_type">${options(assetTypes, asset.asset_type)}</select></div>
        <div class="field"><label>Accountable owner</label><input class="input" name="owner" value="${esc(asset.owner || '')}"></div>
        <div class="field span-2"><label>Programme package</label><select class="input" name="programme_id">${options(facets.programmes.map((p) => ({ value: p.id, label: `${p.package_code} · ${p.title}` })), asset.programme_id, 'Unassigned')}</select></div>
      </div></section>

      <section class="form-section"><div class="form-section-title">Technology and lifecycle evidence</div><div class="form-grid">
        <div class="field"><label>Manufacturer</label><input class="input" name="manufacturer" value="${esc(asset.manufacturer || '')}"></div>
        <div class="field"><label>Model</label><input class="input" name="model" value="${esc(asset.model || '')}"></div>
        <div class="field"><label>Software version</label><input class="input" name="software_version" value="${esc(asset.software_version || '')}"></div>
        <div class="field"><label>Firmware version</label><input class="input" name="firmware_version" value="${esc(asset.firmware_version || '')}"></div>
        <div class="field"><label>Operating system</label><input class="input" name="os_version" value="${esc(asset.os_version || '')}"></div>
        <div class="field"><label>Support status</label><select class="input" name="support_status">${options(facets.support_statuses, asset.support_status)}</select></div>
        <div class="field"><label>Support end date</label><input class="input" type="date" name="support_end_date" value="${esc(asset.support_end_date || '')}"></div>
        <div class="field"><label>Evidence confidence</label><select class="input" name="evidence_confidence">${options([{value:'A',label:'A · Authoritative supplier evidence'},{value:'B',label:'B · Internally verified'},{value:'C',label:'C · Inferred from records'},{value:'D',label:'D · Unknown / unverified'}], asset.evidence_confidence)}</select></div>
        <div class="field"><label>Selected treatment</label><select class="input" name="treatment">${options(facets.treatments, asset.treatment)}</select></div>
      </div></section>

      <section class="form-section"><div class="form-section-title">Risk and delivery assessment</div><div class="form-grid">
        <div class="field"><label>Business criticality</label><select class="input" name="business_criticality">${ratingOptions(asset.business_criticality)}</select></div>
        <div class="field"><label>Safety impact</label><select class="input" name="safety_impact">${ratingOptions(asset.safety_impact)}</select></div>
        <div class="field"><label>Production impact</label><select class="input" name="production_impact">${ratingOptions(asset.production_impact)}</select></div>
        <div class="field"><label>Cyber exposure</label><select class="input" name="cyber_exposure">${ratingOptions(asset.cyber_exposure)}</select></div>
        <div class="field"><label>Failure likelihood</label><select class="input" name="failure_likelihood">${ratingOptions(asset.failure_likelihood)}</select></div>
        <div class="field"><label>Spares risk</label><select class="input" name="spares_risk">${ratingOptions(asset.spares_risk)}</select></div>
        <div class="field"><label>Recoverability risk</label><select class="input" name="recoverability_risk">${ratingOptions(asset.recoverability_risk)}</select></div>
        <div class="field"><label>Dependency complexity</label><select class="input" name="dependency_complexity">${ratingOptions(asset.dependency_complexity)}</select></div>
        <div class="field"><label>Delivery readiness</label><select class="input" name="delivery_readiness">${options([{value:1,label:'1 · Discovery required'},{value:2,label:'2 · Options immature'},{value:3,label:'3 · Defined enough to plan'},{value:4,label:'4 · Design / outage credible'},{value:5,label:'5 · Ready to execute'}], asset.delivery_readiness)}</select></div>
      </div></section>

      <section class="form-section"><div class="form-section-title">Notes and evidence gaps</div><div class="field"><label>Notes</label><textarea class="textarea" name="notes" placeholder="Dependencies, backup evidence, spares, constraints or immediate controls">${esc(asset.notes || '')}</textarea></div></section>
    </div>
    <div class="modal-footer"><div>${id ? `<button class="button ghost" type="button" data-action="delete-asset" data-id="${id}">Delete asset</button>` : ''}</div><div class="modal-footer-right"><button class="button secondary" type="button" data-action="close-modal">Cancel</button><button class="button primary" type="submit">${id ? 'Save assessment' : 'Create asset'}</button></div></div>
  </form>`);
}

async function openProgrammeModal(id = null) {
  const programme = id ? await api(`/api/programmes/${id}`) : {
    package_code: '', title: '', description: '', owner: '', sponsor: '', status: 'discovery', target_wave: 'Unassigned', budget_estimate: 0, contingency_percent: 20,
    target_start: '', target_finish: '', outage_window: '', target_platform: '', dependencies: '', notes: '',
  };
  openModal(`<form id="programme-form" data-id="${id || ''}">
    <div class="modal-header"><div><h2 id="modal-title">${id ? 'Edit programme package' : 'New programme package'}</h2><p>${id ? `${esc(programme.package_code)} · ${programme.asset_count} linked assets` : 'Turn related risks into an investable intervention'}</p></div><button class="icon-button" type="button" data-action="close-modal" aria-label="Close">×</button></div>
    <div class="modal-body">
      ${id ? `<div class="score-preview"><div class="score-preview-value">${programme.average_risk.toFixed(1)}</div><div><strong>${badge(programme.status)} ${badge(programme.target_wave)}</strong><p>${programme.critical_assets} critical assets · ${formatMoney(programme.total_budget)} including contingency</p></div></div>` : ''}
      <section class="form-section"><div class="form-section-title">Package definition</div><div class="form-grid">
        <div class="field"><label>Package code <span class="required">*</span></label><input class="input" required name="package_code" value="${esc(programme.package_code)}" placeholder="OBP-006"></div>
        <div class="field span-2"><label>Title <span class="required">*</span></label><input class="input" required name="title" value="${esc(programme.title)}"></div>
        <div class="field span-3"><label>Problem statement</label><textarea class="textarea" name="description">${esc(programme.description || '')}</textarea></div>
        <div class="field"><label>Owner</label><input class="input" name="owner" value="${esc(programme.owner || '')}"></div>
        <div class="field"><label>Sponsor</label><input class="input" name="sponsor" value="${esc(programme.sponsor || '')}"></div>
        <div class="field"><label>Delivery gate</label><select class="input" name="status">${options(['discovery','options','business_case','design','ready','delivery','acceptance','closed'], programme.status)}</select></div>
        <div class="field"><label>Target wave</label><select class="input" name="target_wave">${options(['Unassigned','Wave 0','Wave 1','Wave 2','Wave 3','Monitor'], programme.target_wave)}</select></div>
        <div class="field"><label>Base estimate (£)</label><input class="input" type="number" min="0" step="1000" name="budget_estimate" value="${esc(programme.budget_estimate)}"></div>
        <div class="field"><label>Contingency (%)</label><input class="input" type="number" min="0" max="100" step="1" name="contingency_percent" value="${esc(programme.contingency_percent)}"></div>
      </div></section>
      <section class="form-section"><div class="form-section-title">Target state and delivery constraints</div><div class="form-grid">
        <div class="field"><label>Target start</label><input class="input" type="date" name="target_start" value="${esc(programme.target_start || '')}"></div>
        <div class="field"><label>Target finish</label><input class="input" type="date" name="target_finish" value="${esc(programme.target_finish || '')}"></div>
        <div class="field"><label>Outage window</label><input class="input" name="outage_window" value="${esc(programme.outage_window || '')}"></div>
        <div class="field span-3"><label>Target platform / state</label><textarea class="textarea" name="target_platform">${esc(programme.target_platform || '')}</textarea></div>
        <div class="field span-3"><label>Dependencies</label><textarea class="textarea" name="dependencies">${esc(programme.dependencies || '')}</textarea></div>
        <div class="field span-3"><label>Programme notes</label><textarea class="textarea" name="notes">${esc(programme.notes || '')}</textarea></div>
      </div></section>
    </div>
    <div class="modal-footer"><div>${id ? `<button class="button ghost" type="button" data-action="delete-programme" data-id="${id}">Delete package</button>` : ''}</div><div class="modal-footer-right"><button class="button secondary" type="button" data-action="close-modal">Cancel</button><button class="button primary" type="submit">${id ? 'Save package' : 'Create package'}</button></div></div>
  </form>`, true);
}

function formPayload(form, numericFields = []) {
  const data = Object.fromEntries(new FormData(form).entries());
  for (const [key, value] of Object.entries(data)) {
    if (value === '') data[key] = null;
  }
  numericFields.forEach((field) => {
    if (data[field] !== null && data[field] !== undefined) data[field] = Number(data[field]);
  });
  return data;
}

function bindUploadZone() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('import-file');
  if (!zone || !input) return;
  const setFile = (file) => {
    state.pendingImportFile = file || null;
    document.getElementById('upload-file-name').textContent = file ? `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB` : 'or select a file from a controlled workspace';
    document.getElementById('upload-title').textContent = file ? 'Ready to validate and import' : 'Drop a UTF-8 CSV here';
  };
  input.addEventListener('change', () => setFile(input.files[0]));
  ['dragenter', 'dragover'].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add('dragging'); }));
  ['dragleave', 'drop'].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove('dragging'); }));
  zone.addEventListener('drop', (event) => setFile(event.dataTransfer.files[0]));
}

async function renderImportResult(result) {
  const target = document.getElementById('import-result');
  if (!target) return;
  target.innerHTML = `<div class="result-grid">
    <div class="result-card"><strong>${result.rows_received}</strong><span>Rows read</span></div>
    <div class="result-card"><strong>${result.created}</strong><span>Created</span></div>
    <div class="result-card"><strong>${result.updated}</strong><span>Updated</span></div>
    <div class="result-card"><strong>${result.failed}</strong><span>Failed</span></div>
  </div>${result.errors.length ? `<ul class="error-list">${result.errors.map((error) => `<li>${esc(error)}</li>`).join('')}</ul>` : ''}`;
}

async function renderCurrent() {
  const requested = (location.hash || '#dashboard').slice(1);
  state.view = Object.hasOwn(pageMeta, requested) ? requested : 'dashboard';
  setPage(state.view);
  try {
    if (state.view === 'assets') await renderAssets();
    else if (state.view === 'programmes') await renderProgrammes();
    else if (state.view === 'data') await renderData();
    else await renderDashboard();
  } catch (error) {
    viewEl.innerHTML = `<div class="empty-state"><div class="empty-symbol">!</div><div><strong>Unable to load this view</strong>${esc(error.message)}</div><button class="button secondary" data-action="retry-view">Try again</button></div>`;
    toast('Application error', error.message, 'error');
  }
}

function navigate(name) {
  if (location.hash === `#${name}`) renderCurrent();
  else location.hash = name;
  sidebar.classList.remove('open');
}

document.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]');
  if (nav) {
    event.preventDefault();
    navigate(nav.dataset.nav);
    return;
  }
  const target = event.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  try {
    if (action === 'refresh-dashboard' || action === 'retry-view') await renderCurrent();
    if (action === 'new-asset') await openAssetModal();
    if (action === 'edit-asset') await openAssetModal(Number(target.dataset.id));
    if (action === 'new-programme') await openProgrammeModal();
    if (action === 'edit-programme') await openProgrammeModal(Number(target.dataset.id));
    if (action === 'close-modal') closeModal();
    if (action === 'clear-asset-filters') {
      Object.assign(state.assets, { offset: 0, q: '', site: '', asset_type: '', support_status: '', risk_band: '', programme_id: '', sort_by: 'risk_score', sort_dir: 'desc' });
      await renderAssets();
    }
    if (action === 'asset-prev') {
      state.assets.offset = Math.max(0, state.assets.offset - state.assets.limit);
      await renderAssets();
    }
    if (action === 'asset-next') {
      state.assets.offset += state.assets.limit;
      await renderAssets();
    }
    if (action === 'select-import-file') document.getElementById('import-file')?.click();
    if (action === 'delete-asset') {
      if (!window.confirm('Delete this asset record? The audit event will remain.')) return;
      const result = await api(`/api/assets/${target.dataset.id}`, { method: 'DELETE' });
      closeModal();
      state.facets = null;
      toast('Asset deleted', result.message);
      await renderCurrent();
    }
    if (action === 'delete-programme') {
      if (!window.confirm('Delete this programme package? Linked assets will become unassigned.')) return;
      const result = await api(`/api/programmes/${target.dataset.id}`, { method: 'DELETE' });
      closeModal();
      state.facets = null;
      state.programmes = null;
      toast('Package deleted', result.message);
      await renderCurrent();
    }
  } catch (error) {
    toast('Action failed', error.message, 'error');
  }
});

document.addEventListener('submit', async (event) => {
  const form = event.target;
  if (form.id === 'global-search-form') {
    event.preventDefault();
    state.assets.q = document.getElementById('global-search').value.trim();
    state.assets.offset = 0;
    navigate('assets');
    return;
  }
  if (form.id === 'asset-filters') {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    Object.assign(state.assets, values, { offset: 0 });
    await renderAssets();
    return;
  }
  if (form.id === 'asset-form') {
    event.preventDefault();
    const numeric = ['business_criticality','safety_impact','production_impact','cyber_exposure','failure_likelihood','spares_risk','recoverability_risk','dependency_complexity','delivery_readiness','programme_id'];
    const payload = formPayload(form, numeric);
    const id = form.dataset.id;
    try {
      const saved = await api(id ? `/api/assets/${id}` : '/api/assets', { method: id ? 'PATCH' : 'POST', body: payload });
      closeModal();
      state.facets = null;
      toast(id ? 'Assessment saved' : 'Asset created', `${saved.asset_code} · ${saved.risk_band} ${saved.risk_score}`);
      await renderCurrent();
    } catch (error) {
      toast('Could not save asset', error.message, 'error');
    }
    return;
  }
  if (form.id === 'programme-form') {
    event.preventDefault();
    const payload = formPayload(form, ['budget_estimate','contingency_percent']);
    const id = form.dataset.id;
    try {
      const saved = await api(id ? `/api/programmes/${id}` : '/api/programmes', { method: id ? 'PATCH' : 'POST', body: payload });
      closeModal();
      state.facets = null;
      state.programmes = null;
      toast(id ? 'Package saved' : 'Package created', `${saved.package_code} · ${saved.title}`);
      await renderCurrent();
    } catch (error) {
      toast('Could not save package', error.message, 'error');
    }
    return;
  }
  if (form.id === 'import-form') {
    event.preventDefault();
    const input = document.getElementById('import-file');
    const file = state.pendingImportFile || input?.files?.[0];
    if (!file) {
      toast('Choose a CSV first', 'No file has been selected.', 'error');
      return;
    }
    const data = new FormData();
    data.append('file', file);
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.textContent = 'Importing…';
    try {
      const result = await api('/api/assets/import', { method: 'POST', body: data });
      await renderImportResult(result);
      state.facets = null;
      state.programmes = null;
      toast('Import complete', `${result.created} created, ${result.updated} updated, ${result.failed} failed`, result.failed ? 'error' : 'success');
    } catch (error) {
      toast('Import failed', error.message, 'error');
    } finally {
      submit.disabled = false;
      submit.textContent = 'Import into database';
    }
  }
});

document.addEventListener('change', async (event) => {
  if (event.target.matches('#asset-filters [data-filter]')) {
    const form = document.getElementById('asset-filters');
    const values = Object.fromEntries(new FormData(form).entries());
    Object.assign(state.assets, values, { offset: 0 });
    await renderAssets();
  }
});

document.getElementById('mobile-menu').addEventListener('click', () => sidebar.classList.toggle('open'));
modalBackdrop.addEventListener('click', (event) => { if (event.target === modalBackdrop) closeModal(); });
document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !modalBackdrop.hidden) closeModal(); });
window.addEventListener('hashchange', renderCurrent);

renderCurrent();
