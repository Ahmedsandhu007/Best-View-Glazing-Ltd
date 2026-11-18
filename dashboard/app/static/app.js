/* The buttons: start a workflow, follow its run, open a tool's inputs, edit repository variables. Plain fetch, no framework. */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  async function post(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(body) });
    let data = {};
    try { data = await r.json(); } catch (e) { data = { error: 'The server answered ' + r.status }; }
    if (!r.ok && !data.error) { data.error = 'The server answered ' + r.status; }
    return data;
  }
  async function get(url) {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    let data = {};
    try { data = await r.json(); } catch (e) { data = { error: 'The server answered ' + r.status }; }
    if (!r.ok && !data.error) { data.error = 'The server answered ' + r.status; }
    return data;
  }
  function show(el, html, cls) {
    el.hidden = false; el.className = 'result' + (cls ? ' ' + cls : ''); el.innerHTML = html;
  }
  function pill(run) {
    const state = run.status !== 'completed' ? 'running' : (run.conclusion === 'success' ? 'ok' : (run.conclusion === 'cancelled' ? 'cancelled' : 'failed'));
    return '<span class="pill ' + state + '">' + esc(run.conclusion || run.status) + '</span>';
  }
  function runLink(run) { return '<a href="' + esc(run.url) + '" target="_blank" rel="noopener">run ' + esc(run.run_number || run.id) + '</a>'; }

  function formInputs(form) {
    const inputs = {}; let confirm = false;
    for (const el of form.querySelectorAll('input, select, textarea')) {
      if (!el.name) continue;
      if (el.type === 'checkbox') { if (el.name === 'confirm') confirm = el.checked; else inputs[el.name] = el.checked ? 'yes' : 'no'; continue; }
      if (String(el.value).trim() !== '') inputs[el.name] = el.value;
    }
    return { inputs, confirm };
  }

  async function startRun(storeId, workflow, inputs, confirm, out, opts) {
    opts = opts || {};
    show(out, 'Starting ' + esc(workflow) + ' ...');
    const data = await post('/api/store/' + storeId + '/run', { workflow, inputs, confirm });
    if (data.error) { show(out, esc(data.error), 'bad'); return; }
    let html = '<strong>' + esc(data.label) + '</strong> started' + (data.live ? ' <span class="pill risk-danger">live</span>' : ' <span class="pill risk-read">dry run / read</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(storeId, data.run.id, out, html, opts); }
    else { html += ' - GitHub has not listed the run yet; it appears under Recent runs within a minute.'; show(out, html, 'good'); }
  }

  function describe(o) {
    // one object of a facts list (an order, a zeroed SKU, a borderline) as "key: value" pairs; true flags shown by name only
    return Object.entries(o).filter(([, v]) => v !== false && v !== '' && v != null)
      .map(([k, v]) => v === true ? esc(k) : (Array.isArray(v) ? esc(k) + ': ' + esc(v.join(', ')) : esc(k.replace(/_/g, ' ')) + ': ' + esc(v))).join(' · ');
  }

  async function pollRun(storeId, runId, out, head, opts) {
    for (let i = 0; i < 240; i++) {
      await new Promise((r) => setTimeout(r, 10000));
      const data = await get('/api/store/' + storeId + '/run/' + runId);
      if (data.error) { show(out, head + '<br>' + esc(data.error), 'bad'); return; }
      const run = data.run;
      if (run.status !== 'completed') { show(out, head + ' ' + pill(run) + ' <span class="muted">(' + ((i + 1) * 10) + ' s)</span>', 'good'); continue; }
      let html = head + ' ' + pill(run);
      if (opts.render && data.facts && Object.keys(data.facts).length) {
        html += opts.render(data.facts);
      } else if (data.facts && Object.keys(data.facts).length) {
        html += '<table class="compact facts">';
        for (const [k, v] of Object.entries(data.facts)) {
          if (Array.isArray(v) && v.length && typeof v[0] === 'object') { html += '<tr><td>' + esc(k.replace(/_/g, ' ')) + '</td><td>' + v.map(describe).join('<br>') + '</td></tr>'; }
          else html += '<tr><td>' + esc(k.replace(/_/g, ' ')) + '</td><td><strong>' + esc(Array.isArray(v) ? v.length : v) + '</strong></td></tr>';
        }
        html += '</table>';
      }
      if (data.lines && data.lines.length) html += '<details open><summary>Key log lines</summary><pre>' + esc(data.lines.join('\n')) + '</pre></details>';
      show(out, html, run.conclusion === 'success' ? 'good' : 'bad');
      if (opts.after && run.conclusion === 'success') { try { await opts.after(run, data); } catch (e) { /* the page offers it again after the reload */ } }
      if (opts.reload && run.conclusion === 'success') setTimeout(() => location.reload(), 1500);
      return;
    }
    show(out, head + '<br>Still running after 40 minutes - follow it on GitHub.', 'good');
  }

  function runFromForm(ev) {
    ev.preventDefault();
    const form = ev.target;
    const { inputs, confirm } = formInputs(form);
    const out = form.querySelector('.result');
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    startRun(form.dataset.store, form.dataset.workflow, inputs, confirm, out, { reload: form.dataset.reload === '1' }).finally(() => { btn.disabled = false; });
    return false;
  }

  async function openTool(storeId, workflow) {
    const panel = document.getElementById('toolpanel');
    panel.innerHTML = '<h2>' + esc(workflow) + '</h2><p class="muted">Loading its inputs ...</p>';
    const def = await get('/api/store/' + storeId + '/workflow/' + workflow);
    if (def.error) { panel.innerHTML = '<h2>' + esc(workflow) + '</h2><p class="error">' + esc(def.error) + '</p>'; return false; }
    let html = '<h2>' + esc(def.label) + ' <span class="pill risk-' + esc(def.risk) + '">' + esc(def.risk) + '</span></h2>';
    html += '<p class="muted">' + esc(def.note || def.name) + (def.schedule && def.schedule.length ? ' · schedule ' + esc(def.schedule.join(', ')) : '') + (def.group ? ' · queue group ' + esc(def.group) : '') + '</p>';
    if (!def.manual) { panel.innerHTML = html + '<p class="error">This workflow has no manual trigger.</p>'; return false; }
    html += '<form class="inputs" data-store="' + esc(storeId) + '" data-workflow="' + esc(workflow) + '" data-risk="' + esc(def.risk) + '" onsubmit="return Dash.runFromForm(event)">';
    const keys = Object.keys(def.inputs || {});
    if (!keys.length) html += '<p class="muted">No inputs.</p>';
    for (const k of keys) {
      const spec = def.inputs[k];
      const words = k === 'mode' ? String(spec.description).split('|').map((w) => w.trim()).filter((w) => /^[a-z]+$/.test(w)) : [];
      const isSwitch = !words.length && (['yes', 'no', 'true', 'false'].includes(String(spec.default).toLowerCase()) || k === def.apply_input);
      html += '<label><strong>' + esc(k) + '</strong>' + (spec.required ? ' <span class="pill risk-danger">required</span>' : '') + '<span class="desc">' + esc(spec.description) + (spec.default !== '' ? ' (default ' + esc(spec.default) + ')' : '') + '</span>';
      if (words.length >= 2) {
        html += '<select name="' + esc(k) + '">' + words.map((o) => '<option value="' + esc(o) + '"' + (o === spec.default ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select>';
      } else if (spec.options && spec.options.length) {
        html += '<select name="' + esc(k) + '">' + spec.options.map((o) => '<option value="' + esc(o) + '"' + (o === spec.default ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select>';
      } else if (isSwitch) {
        const d = String(spec.default).toLowerCase();
        html += '<select name="' + esc(k) + '"><option value="yes"' + (d === 'yes' || d === 'true' ? ' selected' : '') + '>yes</option><option value="no"' + (d === 'no' || d === 'false' || d === '' ? ' selected' : '') + '>no</option></select>';
      } else if (spec.description.length > 60 || /comma|list|rules|regex/i.test(spec.description)) {
        html += '<textarea name="' + esc(k) + '" placeholder="' + esc(spec.default) + '"></textarea>';
      } else {
        html += '<input type="text" name="' + esc(k) + '" placeholder="' + esc(spec.default) + '">';
      }
      html += '</label>';
    }
    if (def.risk === 'danger') html += '<label class="confirm"><input type="checkbox" name="confirm"> I understand this changes the store for real when the apply switch is on</label>';
    html += '<p><button type="submit">Start</button> <span class="muted">Empty fields keep the workflow\'s defaults.</span></p><div class="result" hidden></div></form>';
    panel.innerHTML = html;
    return false;
  }

  async function loadVariables(storeId, storeName) {
    const box = document.getElementById('variables');
    box.innerHTML = '<p class="muted">Loading ' + esc(storeName) + ' ...</p>';
    const data = await get('/api/store/' + storeId + '/variables');
    if (data.error) { box.innerHTML = '<p class="error">' + esc(data.error) + '</p>'; return false; }
    let html = '<h3>' + esc(storeName) + '</h3><table class="compact"><tr><th>Variable</th><th>Value</th><th>Changed</th><th></th></tr>';
    for (const v of data.variables) {
      html += '<tr><td><code>' + esc(v.name) + '</code></td><td><input type="text" data-name="' + esc(v.name) + '" value="' + esc(v.value) + '"></td><td class="muted">' + esc((v.updated_at || '').slice(0, 10)) + '</td>' +
        '<td><button class="ghost" onclick="return Dash.saveVariable(\'' + esc(storeId) + '\', this)">Save</button></td></tr>';
    }
    html += '<tr><td><input type="text" id="newvar" placeholder="NEW_NAME"></td><td><input type="text" id="newval" placeholder="value"></td><td></td><td><button class="ghost" onclick="return Dash.saveVariable(\'' + esc(storeId) + '\', this, true)">Add</button></td></tr>';
    html += '</table><label class="confirm"><input type="checkbox" id="varconfirm"> I understand the store\'s next runs will use the new value</label><div class="result" id="varresult" hidden></div>';
    box.innerHTML = html;
    return false;
  }

  async function saveVariable(storeId, btn, isNew) {
    const out = document.getElementById('varresult');
    let name, value;
    if (isNew) { name = document.getElementById('newvar').value.trim(); value = document.getElementById('newval').value; }
    else { const input = btn.closest('tr').querySelector('input[data-name]'); name = input.dataset.name; value = input.value; }
    const confirm = document.getElementById('varconfirm').checked;
    const data = await post('/api/store/' + storeId + '/variables', { name, value, confirm });
    if (data.error) show(out, esc(data.error), 'bad'); else show(out, 'Saved <code>' + esc(data.name) + '</code> = ' + esc(data.value), 'good');
    return false;
  }

  // ---- store readiness (Settings) ----
  let rdStore = '', rdStoreName = '';
  async function loadReadiness(storeId, storeName) {
    rdStore = storeId; rdStoreName = storeName;
    const box = document.getElementById('readiness');
    box.innerHTML = '<p class="muted">Comparing ' + esc(storeName) + ' against the other stores ...</p>';
    const data = await get('/api/stores/' + storeId + '/readiness');
    if (data.error) { box.innerHTML = '<p class="error">' + esc(data.error) + '</p>'; return false; }
    let html = '<h3>' + esc(storeName) + ' <small class="muted">against ' + data.compared_against.length + ' other store(s)</small></h3>';
    if (data.ready && !data.secret_gaps.length && !data.variable_gaps.length) html += '<p><span class="pill ok">ready</span> <span class="muted">nothing missing, nothing parked.</span></p>';
    if (data.secrets_missing.length) {
      html += '<p><span class="pill failed">missing secrets</span> ' + data.secrets_missing.map((n) => '<code>' + esc(n) + '</code>').join(' ') +
        ' <span class="muted">- set them in the Repository secrets card.</span></p>';
    }
    if (data.secret_gaps.length) {
      html += '<p><span class="pill quiet">fleet secrets</span> ' + data.secret_gaps.map((g) => '<code>' + esc(g.name) + '</code> <span class="muted">(' + g.held_by + ' store(s) have it)</span>').join(', ') + '</p>';
    }
    if (data.variable_gaps.length) {
      html += '<h4>Variables the fleet carries that ' + esc(storeName) + ' lacks</h4><table class="compact"><tr><th>Variable</th><th>Held by</th><th>Value to set</th><th></th></tr>';
      for (const g of data.variable_gaps) {
        html += '<tr><td><code>' + esc(g.name) + '</code></td><td class="muted">' + g.held_by + ' store(s)</td>' +
          '<td><input type="text" data-name="' + esc(g.name) + '" value="' + esc(g.value) + '" placeholder="' + (g.value ? '' : 'the siblings differ - type this store\'s own value') + '"></td>' +
          '<td><button class="ghost" onclick="return Dash.rdAdopt(this)">Set</button></td></tr>';
      }
      html += '</table>';
    }
    if (data.parked.length) {
      html += '<h4>Parked workflows</h4><table class="compact"><tr><th>Workflow</th><th>File</th><th></th></tr>';
      for (const w of data.parked) {
        html += '<tr><td>' + esc(w.name) + '</td><td><code>' + esc(w.path) + '</code></td><td><button class="ghost" onclick="return Dash.rdWorkflow(\'' + esc(w.path) + '\', \'enable\')">Enable</button></td></tr>';
      }
      html += '</table>';
    } else {
      html += '<p class="muted">Every workflow is on (' + data.workflows.length + ' active).</p>';
    }
    if (data.off_on_purpose && data.off_on_purpose.length) {
      html += '<p><span class="pill quiet">eBay only</span> <span class="muted">' + data.off_on_purpose.length + ' Amazon workflow(s) are off on purpose and not counted: ' +
        data.off_on_purpose.map((w) => '<code>' + esc(w.path) + '</code>').join(' ') + '</span></p>';
    }
    html += '<details><summary class="muted">All ' + data.workflows.length + ' workflows (park one here)</summary><table class="compact">';
    for (const w of data.workflows) {
      const on = w.state === 'active';
      html += '<tr><td>' + esc(w.name) + '</td><td><code>' + esc(w.path) + '</code></td><td>' + (on ? '<span class="pill ok">on</span>' : '<span class="pill failed">parked</span>') +
        '</td><td><button class="ghost" onclick="return Dash.rdWorkflow(\'' + esc(w.path) + '\', \'' + (on ? 'disable' : 'enable') + '\')">' + (on ? 'Park' : 'Enable') + '</button></td></tr>';
    }
    html += '</table></details>';
    html += '<label class="confirm"><input type="checkbox" id="rdconfirm"> I understand: a set variable counts from the next run, an enabled workflow\'s schedule starts at its next tick</label><div class="result" id="rdresult" hidden></div>';
    box.innerHTML = html;
    return false;
  }
  async function rdAdopt(btn) {
    const out = document.getElementById('rdresult');
    const input = btn.closest('tr').querySelector('input[data-name]');
    if (!input.value.trim()) { show(out, 'Type the value first - the siblings hold different values for this one.', 'bad'); return false; }
    const data = await post('/api/store/' + rdStore + '/variables', { name: input.dataset.name, value: input.value, confirm: document.getElementById('rdconfirm').checked });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, 'Saved <code>' + esc(data.name) + '</code> = ' + esc(data.value), 'good');
    return loadReadiness(rdStore, rdStoreName);
  }
  async function rdWorkflow(path, action) {
    const out = document.getElementById('rdresult');
    const data = await post('/api/stores/' + rdStore + '/workflows', { path, action, confirm: document.getElementById('rdconfirm').checked });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, (action === 'enable' ? 'Enabled' : 'Parked') + ' <code>' + esc(data.path) + '</code>', 'good');
    return loadReadiness(rdStore, rdStoreName);
  }

  // ---- pricing card ----
  function pricingRoot() { return document.getElementById('pricing'); }
  function readBands() {
    const rows = Array.from(document.querySelectorAll('#bands tr')).slice(1);
    return rows.map((tr) => {
      const b = tr.querySelector('.bound').value.trim(); const p = tr.querySelector('.profit').value.trim();
      return [b === '' ? null : Number(b), p === '' ? NaN : Number(p)];
    });
  }
  function readWindows() {
    const table = document.getElementById('windows');
    if (!table) return null;
    return Array.from(table.querySelectorAll('tr')).slice(1).map((tr) => [Number(tr.querySelector('.lo').value), Number(tr.querySelector('.hi').value), Number(tr.querySelector('.pct').value)]);
  }
  function addBand() {
    const table = document.getElementById('bands');
    const tr = document.createElement('tr');
    tr.innerHTML = '<td><input type="number" step="0.01" min="0.01" class="bound"></td><td><input type="number" step="0.5" min="0" max="1000" class="profit" value="20"></td><td><button type="button" class="ghost" onclick="return Dash.removeBand(this)">remove</button></td>';
    table.appendChild(tr);
    return false;
  }
  function addWindow() {
    const table = document.getElementById('windows');
    const tr = document.createElement('tr');
    tr.innerHTML = '<td><input type="number" step="0.01" min="0" class="lo" value="10"></td><td><input type="number" step="0.01" min="0" class="hi" value="20"></td><td><input type="number" step="0.5" min="0" max="1000" class="pct" value="15"></td><td><button type="button" class="ghost" onclick="return Dash.removeBand(this)">remove</button></td>';
    table.appendChild(tr);
    return false;
  }
  function removeBand(btn) { btn.closest('tr').remove(); return false; }

  function bandProfit(bands, total) {
    if (!bands || !bands.length) return null;
    if (bands[0][0] !== null && total < bands[0][0]) return bands[0][1];
    const rest = bands[0][0] !== null ? bands.slice(1) : bands;
    for (const [bound, profit] of rest) { if (bound === null || total <= bound) return profit; }
    return bands[bands.length - 1][1];
  }
  function calc() {
    const total = Number(document.getElementById('calcCost').value); const fee = Number(document.getElementById('calcFee').value);
    const bands = readBands();
    const out = document.getElementById('calcOut');
    if (!(total > 0) || !(fee >= 0) || bands.some((b) => isNaN(b[1]))) { out.textContent = 'Enter a cost and a commission.'; return false; }
    const profit = bandProfit(bands, total); const eff = fee * 1.2;
    const price = total * (1 + profit / 100) / (1 - eff / 100);
    out.innerHTML = 'Band profit <strong>' + esc(profit) + '%</strong>; OnBuy takes ' + esc(eff.toFixed(2)) + '% (' + esc(fee) + '% + VAT); selling price <strong>£' + esc(price.toFixed(2)) + '</strong>' +
      ' = £' + esc(total.toFixed(2)) + ' x ' + esc((1 + profit / 100).toFixed(2)) + ' / ' + esc((1 - eff / 100).toFixed(4)) + '. A selling-price window, if the store has one, may override the band.';
    return false;
  }

  async function pricingStart(url, body, out, label) {
    show(out, label + ' ...');
    const data = await post(url, body);
    if (data.error) { show(out, esc(data.error), 'bad'); return; }
    let html = '<strong>' + esc(data.label || label) + '</strong> started' + (data.live ? ' <span class="pill risk-danger">live</span>' : ' <span class="pill risk-read">dry run</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.setting) html += '<details><summary>Schedule sent</summary><pre>' + esc(data.setting) + '</pre></details>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(pricingRoot().dataset.store, data.run.id, out, html, {}); }
    else { html += ' - GitHub has not listed the run yet; it appears under Recent runs within a minute.'; show(out, html, 'good'); }
  }
  function pricingPreview() {
    const storeId = pricingRoot().dataset.store;
    pricingStart('/api/store/' + storeId + '/pricing/preview', { bands: readBands(), overrides: readWindows() }, document.getElementById('previewResult'), 'Preview');
    return false;
  }
  function pricingApply() {
    const storeId = pricingRoot().dataset.store;
    pricingStart('/api/store/' + storeId + '/pricing/apply', { bands: readBands(), overrides: readWindows(), confirm: document.getElementById('applyConfirm').checked }, document.getElementById('applyResult'), 'Apply');
    return false;
  }
  function pricingPush() {
    const storeId = pricingRoot().dataset.store;
    startRun(storeId, 'audit_price_drift.yml', { fix: 'yes' }, document.getElementById('pushConfirm').checked, document.getElementById('pushResult'), {});
    return false;
  }

  // ---- fees card ----
  async function saveFeeMode() {
    const root = document.getElementById('fees');
    const out = document.getElementById('modeResult');
    const body = { mode: document.getElementById('feeMode').value, tier_mode: document.getElementById('tierMode').value, confirm: document.getElementById('modeConfirm').checked };
    const data = await post('/api/store/' + root.dataset.store + '/fees/mode', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, 'Saved: FEE_MODE = ' + esc(data.mode) + ', FEE_TIER_MODE = ' + esc(data.tier_mode) + '. The store\'s next runs price with it.', 'good');
    setTimeout(() => location.reload(), 1500);
    return false;
  }

  // ---- sale card ----
  function saleRoot() { return document.getElementById('sale'); }
  function saleRows() { return Array.from(document.querySelectorAll('#sranges tr.srow')); }
  const USUAL = [[0, 4.99], [5, 9.99], [10, 20], [20.01, 50], [50.01, null]];
  function saleRowHtml(lo, hi, pct) {
    return '<td><input type="number" step="0.01" min="0" class="sfrom" value="' + (lo == null ? '' : lo) + '"></td>' +
      '<td><input type="number" step="0.01" min="0" class="sto" value="' + (hi == null ? '' : hi) + '"></td>' +
      '<td><input type="number" step="0.5" min="0" max="90" class="spct" placeholder="none" value="' + (pct == null ? '' : pct) + '"></td>' +
      '<td><button type="button" class="ghost" onclick="return Dash.saleRemove(this)">remove</button></td>';
  }
  function saleAdd() {
    const tr = document.createElement('tr'); tr.className = 'srow'; tr.innerHTML = saleRowHtml(null, null, null);
    document.getElementById('sranges').appendChild(tr); return false;
  }
  function saleRemove(btn) { btn.closest('tr').remove(); return false; }
  function saleReset() {
    saleRows().forEach((tr) => tr.remove());
    USUAL.forEach(([lo, hi]) => { const tr = document.createElement('tr'); tr.className = 'srow'; tr.innerHTML = saleRowHtml(lo, hi, null); document.getElementById('sranges').appendChild(tr); });
    return false;
  }
  function saleFill() {
    const v = document.getElementById('fillPct').value;
    if (v === '') return false;
    saleRows().forEach((tr) => { const p = tr.querySelector('.spct'); if (p.value === '') p.value = v; });
    return false;
  }
  function saleBody(extra) {
    const ranges = saleRows().map((tr) => [tr.querySelector('.sfrom').value, tr.querySelector('.sto').value, tr.querySelector('.spct').value]);
    return Object.assign({ ranges, sale_end: document.getElementById('saleEnd').value, min_profit: document.getElementById('floorPct').value,
      floor_mode: document.getElementById('floorMode').value, scope: document.getElementById('saleScope').value }, extra || {});
  }
  const money = (n) => Number(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function renderSale(f) {
    let html = '';
    if (f.sale) html += '<p>' + esc(String(f.sale).replace(/GBP /g, '£')) + (f.window_end ? ' <span class="muted">· last day ' + esc(String(f.window_end).slice(0, 10)) + '</span>' : '') + '</p>';
    html += '<table class="compact facts">';
    if (f.listings != null) html += '<tr><td>Listings on the account</td><td><strong>' + esc(f.listings) + '</strong>' + (f.sales_now != null ? ' <span class="muted">(' + esc(f.sales_now) + ' carried a sale before the run)</span>' : '') + '</td></tr>';
    if (f.on_sale_after != null) html += '<tr><td>On sale after the run</td><td><strong>' + esc(f.on_sale_after) + '</strong> <span class="muted">· £' + esc(money(f.discount)) + ' off in total if each sold once</span></td></tr>';
    if (f.updates != null) html += '<tr><td>Updates to send</td><td>' + esc(f.updates) + ' in ' + esc(f.requests) + ' request(s)</td></tr>';
    if (f.applied_ok != null) html += '<tr><td>Applied</td><td><strong>' + esc(f.applied_ok) + '</strong> ok, ' + esc(f.applied_failed) + ' failed' + (f.readback ? ' <span class="muted">· read-back ' + esc(f.readback) + ' showing</span>' : '') + '</td></tr>';
    if (f.cancelled_ok != null) html += '<tr><td>Sales ended</td><td><strong>' + esc(f.cancelled_ok) + '</strong> ok, ' + esc(f.cancelled_failed) + ' failed' + (f.state_removed ? ' <span class="muted">· sale file removed</span>' : '') + '</td></tr>';
    if (f.test_sku) html += '<tr><td>Test listing</td><td><code>' + esc(f.test_sku) + '</code> ' + esc(f.test_plan || '') + (f.test_on ? '<br>sale on: ' + esc(f.test_on) : '') + (f.test_off ? '<br>sale off: ' + esc(f.test_off) : '') + '</td></tr>';
    html += '</table>';
    if (f.ranges && f.ranges.length) {
      html += '<table class="compact"><tr><th>#</th><th>Prices</th><th>Sale</th><th>Listings</th><th>On sale</th><th>No cost</th><th>Under floor</th><th>Other</th><th>£ off</th></tr>';
      for (const r of f.ranges) html += '<tr><td>' + esc(r.range) + '</td><td>' + esc(r.prices) + '</td><td>' + esc(r.sale) + '</td><td>' + esc(r.listings) + '</td><td><strong>' + esc(r.on_sale) + '</strong></td><td class="muted">' + esc(r.no_cost) + '</td><td class="muted">' + esc(r.below_floor) + '</td><td class="muted">' + esc(r.other) + (r.ended ? ' (+' + esc(r.ended) + ' ended)' : '') + '</td><td>' + esc(money(r.discount)) + '</td></tr>';
      if (f.outside) html += '<tr><td colspan="9" class="muted">' + esc(f.outside) + ' listings are outside every range and get no sale.</td></tr>';
      html += '</table>';
    } else if (f.actions && f.actions.length) {
      html += '<table class="compact"><tr><th>What happens</th><th>Listings</th></tr>' + f.actions.map((a) => '<tr><td>' + esc(a.action) + '</td><td>' + esc(a.listings) + '</td></tr>').join('') + '</table>';
    }
    return html;
  }
  async function saleStart(mode, body, out, label, opts) {
    show(out, label + ' ...');
    const storeId = saleRoot().dataset.store;
    const data = await post('/api/store/' + storeId + '/sale/' + mode, body);
    if (data.error) { show(out, esc(data.error), 'bad'); return; }
    let html = '<strong>' + esc(data.label || label) + '</strong> started' + (data.live ? ' <span class="pill risk-danger">live</span>' : ' <span class="pill risk-read">preview</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(storeId, data.run.id, out, html, Object.assign({ render: renderSale }, opts || {})); }
    else { html += ' - GitHub has not listed the run yet; it appears under Last run within a minute.'; show(out, html, 'good'); }
  }
  function salePreview() { saleStart('plan', saleBody(), document.getElementById('salePreviewResult'), 'Preview'); return false; }
  function saleApply() { saleStart('apply', saleBody({ confirm: document.getElementById('applyConfirm').checked }), document.getElementById('saleApplyResult'), 'Apply', { reload: true }); return false; }
  function saleTest() { saleStart('test', saleBody({ confirm: document.getElementById('testConfirm').checked, test_sku: document.getElementById('testSku').value }), document.getElementById('saleTestResult'), 'Test'); return false; }
  function saleCancel() { saleStart('cancel', { confirm: document.getElementById('cancelConfirm').checked }, document.getElementById('cancelResult'), 'Cancel', { reload: true }); return false; }

  // ---- catalogue card ----
  function catStore() { return document.getElementById('catalogue').dataset.store; }
  function catPicked() { return Array.from(document.querySelectorAll('#holds .cksel:checked')).map((b) => b.value); }
  const catChecked = (id) => { const el = document.getElementById(id); return !!(el && el.checked); };
  function catFiles(files) {
    return (files || []).map((f) => esc(f.file) + (f.changed ? ' (<a href="' + esc(f.url) + '" target="_blank" rel="noopener">commit ' + esc(f.commit) + '</a>)' : ' (nothing to change)')).join(', ');
  }
  function renderRemoval(f) {
    let html = '<table class="compact facts">';
    if (f.asked != null) html += '<tr><td>Asked for</td><td>' + esc(f.asked) + ' listing(s), ' + esc(f.mode || '') + '</td></tr>';
    if (f.planned != null && f.deleted == null) html += '<tr><td>Would be removed</td><td><strong>' + esc(f.planned) + '</strong></td></tr>';
    if (f.deleted != null) html += '<tr><td>Deleted from the sheet</td><td><strong>' + esc(f.deleted) + '</strong> of ' + esc(f.planned) + ' planned' + (f.still_on_sale != null ? '' : '') + '</td></tr>';
    if (f.still_on_sheet != null) html += '<tr><td>Check afterwards</td><td>' + esc(f.still_on_sheet) + ' removed SKU(s) still on the sheet</td></tr>';
    if (f.hold_lines_dropped != null) html += '<tr><td>Hold list lines dropped</td><td>' + esc(f.hold_lines_dropped) + '</td></tr>';
    html += '</table>';
    if (f.will_remove && f.will_remove.length) {
      html += '<table class="compact"><tr><th>Row</th><th>SKU</th><th>Overlap</th><th>The row says</th><th>The page says</th><th>Stock sheet / OnBuy</th></tr>';
      for (const r of f.will_remove) html += '<tr><td>' + esc(r.tab) + ' ' + esc(r.row) + '</td><td><code>' + esc(r.sku) + '</code></td><td>' + esc(Math.round(r.overlap * 100)) + '%</td><td>' + esc(r.row_title) + '</td><td>' + esc(r.page_name) + '</td><td class="muted">' + esc(r.sheet_stock) + ' / ' + esc(r.onbuy_stock) + '</td></tr>';
      html += '</table>';
    }
    if (f.held_back && f.held_back.length) html += '<p><strong>Held back</strong> (not removed): ' + f.held_back.map((h) => '<code>' + esc(h.sku) + '</code> ' + esc(h.why)).join('; ') + '</p>';
    if (f.onbuy) html += '<p>OnBuy listings: ' + Object.entries(f.onbuy).map(([k, v]) => '<strong>' + esc(v) + '</strong> ' + esc(k)).join(', ') + '</p>';
    if (f.suspended && f.suspended.length) html += '<p><strong>Delete these by hand on OnBuy</strong> (suspended, the API refuses): ' + f.suspended.map((s) => '<code>' + esc(s) + '</code>').join(' ') + '</p>';
    if (f.errors && f.errors.length) html += '<p class="bad-text">OnBuy errors: ' + f.errors.map((e) => '<code>' + esc(e.sku) + '</code> ' + esc(e.why)).join('; ') + '</p>';
    if (f.nothing) html += '<p class="muted">Nothing to remove.</p>';
    return html;
  }
  function renderPurge(f) {
    let html = '<table class="compact facts">';
    if (f.rows != null) html += '<tr><td>eBay tab rows</td><td>' + esc(f.rows) + '</td></tr><tr><td>Look dead</td><td>brand-blocked <strong>' + esc(f.brand) + '</strong>, out of stock <strong>' + esc(f.oos) + '</strong>, held back ' + esc(f.held_back) + '</td></tr>';
    if (f.ebay_gone != null) html += '<tr><td>eBay confirms (out of stock)</td><td>gone ' + esc(f.ebay_gone) + ', alive again ' + esc(f.ebay_alive) + ', unknown ' + esc(f.ebay_unknown) + '</td></tr>';
    if (f.to_delete != null) html += '<tr><td>Would delete this run</td><td><strong>' + esc(f.to_delete) + '</strong> row(s)</td></tr>';
    if (f.done != null) html += '<tr><td>Removed</td><td><strong>' + esc(f.done) + '</strong> (brand ' + esc(f.done_brand) + ', out of stock ' + esc(f.done_oos) + ')' + (f.suspended_count ? ', ' + esc(f.suspended_count) + ' suspended on OnBuy' : '') + (f.onbuy_errors ? ', ' + esc(f.onbuy_errors) + ' OnBuy errors' : '') + '</td></tr>';
    if (f.suspended_total != null) html += '<tr><td>Purged listings OnBuy would not delete</td><td><strong>' + esc(f.suspended_total) + '</strong></td></tr>';
    html += '</table>';
    if (f.held && f.held.length) html += '<p class="muted">Held back: ' + f.held.map((h) => esc(h.rows) + ' ' + esc(h.why)).join('; ') + '</p>';
    if (f.suspended && f.suspended.length) html += '<p><strong>Delete these by hand on OnBuy</strong> (suspended):</p><table class="compact">' + f.suspended.map((s) => '<tr><td><code>' + esc(s.sku) + '</code></td><td>' + esc(s.title) + '</td></tr>').join('') + '</table>';
    if (f.nothing) html += '<p class="muted">Nothing to purge.</p>';
    return html;
  }
  async function catRelease(same) {
    const out = document.getElementById('catResult'); const skus = catPicked();
    if (!skus.length) { show(out, 'Tick at least one listing first.', 'bad'); return false; }
    show(out, 'Working ...');
    const data = await post('/api/store/' + catStore() + '/catalogue/release', { skus, same_product: same, confirm: catChecked('catConfirm') });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, 'Released <strong>' + esc(data.released.length) + '</strong> listing(s)' + (data.same_product ? ' and added them to the same-product list' : '') + '. Edited: ' + catFiles(data.files) + '. They get their stock back at the next sync.', 'good');
    setTimeout(() => location.reload(), 3500);
    return false;
  }
  async function catDelete(dry) {
    const out = document.getElementById('catResult'); const skus = catPicked();
    if (!skus.length) { show(out, 'Tick at least one listing first.', 'bad'); return false; }
    show(out, 'Starting ...');
    const data = await post('/api/store/' + catStore() + '/catalogue/delete', { skus, dry_run: dry, confirm: catChecked('catConfirm') });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>' + (dry === 'yes' ? 'Delete check (dry run)' : 'Delete') + '</strong> started' + (data.live ? ' <span class="pill risk-danger">live</span>' : ' <span class="pill risk-read">dry run</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    const after = async () => {          // the run does not edit the hold lists: drop the lines of what it deleted (the server works out which those are)
      const r = await post('/api/store/' + catStore() + '/catalogue/forget', {});
      out.insertAdjacentHTML('beforeend', r.error ? '<p class="bad-text">The hold lists were not cleaned: ' + esc(r.error) + '</p>'
        : (r.forgotten.length ? '<p>Dropped ' + esc(r.forgotten.length) + ' line(s) of the deleted listings from the hold lists: ' + catFiles(r.files) + '.</p>' : ''));
    };
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(catStore(), data.run.id, out, html, { render: renderRemoval, reload: dry !== 'yes', after: dry === 'yes' ? null : after }); }
    else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }
  async function catForget() {
    const out = document.getElementById('goneResult');
    out.textContent = 'Working ...';
    const data = await post('/api/store/' + catStore() + '/catalogue/forget', {});
    if (data.error) { out.textContent = data.error; return false; }
    out.innerHTML = 'Dropped ' + esc(data.forgotten.length) + ' line(s): ' + catFiles(data.files) + '.';
    setTimeout(() => location.reload(), 2500);
    return false;
  }
  async function catFreeze() {
    const out = document.getElementById('freezeResult');
    show(out, 'Working ...');
    const data = await post('/api/store/' + catStore() + '/catalogue/freeze', { skus: document.getElementById('freezeSkus').value, reason: document.getElementById('freezeReason').value,
      zero_now: catChecked('freezeZero'), confirm: catChecked('freezeConfirm') });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = 'Frozen <strong>' + esc(data.frozen.length) + '</strong> listing(s). Edited: ' + catFiles(data.files) + '.';
    if (data.zero && data.zero.run) html += ' Taking their stock off OnBuy now: ' + runLink(data.zero.run) + '.';
    else if (data.zero_error) html += ' <span class="bad-text">The stock was not taken off OnBuy now: ' + esc(data.zero_error) + ' The next nightly does it.</span>';
    else html += ' The next nightly takes their stock off.';
    show(out, html, data.zero_error ? 'bad' : 'good');
    setTimeout(() => location.reload(), 4500);
    return false;
  }
  async function catPurge(suspended) {
    const out = document.getElementById('purgeResult');
    show(out, 'Starting ...');
    const data = await post('/api/store/' + catStore() + '/catalogue/purge', { suspended: !!suspended });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>' + (suspended ? 'Suspended listings' : 'Purge dry run') + '</strong> started <span class="pill risk-read">' + (suspended ? 'read only' : 'dry run') + '</span>';
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(catStore(), data.run.id, out, html, { render: renderPurge }); }
    else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }

  // ---- delete card ----
  let delPlanned = null;                 // the request body whose plan finished well; "Delete for real" waits for the same body
  function delStore() { return document.getElementById('delete').dataset.store; }
  function delBody() {
    return { skus: document.getElementById('delSkus').value, backup_tab: document.getElementById('delBackup').value, allow_in_stock: !!document.getElementById('delStock').checked };
  }
  function delSync() {
    const typed = document.getElementById('delSkus').value.split(/[,\s]+/).filter(Boolean);
    const unique = new Set(typed).size;
    document.getElementById('delCount').textContent = unique + ' SKU' + (unique === 1 ? '' : 's') + (typed.length > unique ? ' (' + (typed.length - unique) + ' repeated)' : '');
    document.getElementById('delApply').disabled = !(delPlanned && delPlanned === JSON.stringify(delBody()));
  }
  function loadSkuFile(input, boxId, after) {
    // a text or CSV file: the first column of every line is a SKU (a "SKU" header line is dropped)
    const file = input.files && input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const lines = String(reader.result).split(/\r?\n/).map((l) => l.split(',')[0].replace(/^"|"$/g, '').trim()).filter(Boolean);
      if (lines.length && /^sku$/i.test(lines[0])) lines.shift();
      document.getElementById(boxId).value = lines.join('\n');
      after();
    };
    reader.readAsText(file);
  }
  function delFile(input) { loadSkuFile(input, 'delSkus', delSync); }
  const codes = (list) => (list || []).map((s) => '<code>' + esc(s) + '</code>').join(' ');
  function renderCheck(d) {
    let html = '<strong>' + esc(d.count) + '</strong> SKU(s) can go' + (d.unique > d.count ? ' (of ' + esc(d.unique) + ' in the list)' : '') + (d.pasted > d.unique ? '; ' + esc(d.pasted - d.unique) + ' repeat(s) dropped' : '') + '.';
    if (d.held_count) html += '<p><strong>' + esc(d.held_count) + '</strong> kept out because they are on the hold lists (release them on the Catalogue page first): ' + codes(d.held) + (d.held_count > d.held.length ? ' ...' : '') + '</p>';
    if (d.on_orders_count) html += '<p><strong>' + esc(d.on_orders_count) + '</strong> kept out because they are on an open order (the row is needed to fulfil it): ' + codes(d.on_orders) + (d.on_orders_count > d.on_orders.length ? ' ...' : '') + '</p>';
    html += '<p class="muted">Open-order data: ' + (d.orders_hours == null ? 'none' : d.orders_hours.toFixed(1) + ' h old, ' + esc(d.orders_count) + ' orders') + '.</p>';
    return html;
  }
  function renderGuarded(f) {
    let html = '<table class="compact facts">';
    if (f.listed != null) html += '<tr><td>SKUs in the list</td><td><strong>' + esc(f.listed) + '</strong>' + (f.in_stock_ok ? ' <span class="pill risk-danger">rows with stock go too</span>' : '') + '</td></tr>';
    if (f.planned != null && f.deleted == null) html += '<tr><td>Rows that would go</td><td><strong>' + esc(f.planned) + '</strong>' + (f.live != null ? ' (live on OnBuy ' + esc(f.live) + ', showing stock ' + esc(f.in_stock) + ')' : '') + '</td></tr>';
    if (f.deleted != null) html += '<tr><td>Rows removed from the sheet</td><td><strong>' + esc(f.deleted) + '</strong> of ' + esc(f.planned) + ' planned' + (f.backup ? ', copied first to <code>' + esc(f.backup.tab) + '</code> (' + esc(f.backup.rows) + ' rows)' : '') + '</td></tr>';
    if (f.still_on_sheet != null) html += '<tr><td>Check afterwards</td><td>' + esc(f.still_on_sheet) + ' removed SKU(s) still on the sheet</td></tr>';
    if (f.absent != null) html += '<tr><td>Not on the sheet</td><td>' + esc(f.absent) + ' (their OnBuy listing is deleted anyway)</td></tr>';
    if (f.onbuy_list != null) html += '<tr><td>OnBuy listings to delete</td><td><strong>' + esc(f.onbuy_list) + '</strong></td></tr>';
    if (f.never != null) html += '<tr><td>Never touched</td><td>' + esc(f.never) + ' SKUs on the protected list and the exclusions</td></tr>';
    if (f.onbuy) html += '<tr><td>OnBuy answered</td><td>' + Object.entries(f.onbuy).map(([k, v]) => '<strong>' + esc(v) + '</strong> ' + esc(k)).join(', ') + '</td></tr>';
    html += '</table>';
    if (f.will_remove && f.will_remove.length) html += '<table class="compact"><tr><th>Rows</th><th>Tab</th><th>Why they go</th></tr>' + f.will_remove.map((r) => '<tr><td>' + esc(r.n) + '</td><td>' + esc(r.tab) + '</td><td>' + esc(r.reason) + '</td></tr>').join('') + '</table>';
    if (f.held && f.held_reasons && f.held_reasons.length) html += '<p><strong>Held back (' + esc(f.held) + '):</strong></p><table class="compact"><tr><th>Rows</th><th>Tab</th><th>Why</th></tr>' + f.held_reasons.map((r) => '<tr><td>' + esc(r.n) + '</td><td>' + esc(r.tab) + '</td><td>' + esc(r.why) + '</td></tr>').join('') + '</table>';
    if (f.held_rows && f.held_rows.length) html += '<details><summary>Held-back rows (the first ' + esc(f.held_rows.length) + ')</summary><table class="compact"><tr><th>Tab</th><th>Row</th><th>SKU</th><th>Stock</th><th>Why</th></tr>' + f.held_rows.map((r) => '<tr><td>' + esc(r.tab) + '</td><td>' + esc(r.row) + '</td><td><code>' + esc(r.sku) + '</code></td><td>' + esc(r.stock) + '</td><td>' + esc(r.why) + '</td></tr>').join('') + '</table></details>';
    if (f.refused) html += '<p class="bad-text"><strong>Refused:</strong> the plan holds ' + esc(f.refused.rows) + ' rows, above the limit of ' + esc(f.refused.max) + ' - nothing was changed.</p>';
    if (f.skipped && f.skipped.length) html += '<p class="bad-text">Skipped at deletion time (the SKU was on other than one row): ' + f.skipped.map((s) => '<code>' + esc(s.sku) + '</code> (' + esc(s.rows) + ' rows)').join(' ') + '</p>';
    if (f.suspended && f.suspended.length) html += '<p><strong>Delete these by hand on OnBuy</strong> (suspended, the API refuses): ' + codes(f.suspended) + '</p>';
    if (f.already_gone && f.already_gone.length) html += '<p class="muted">' + esc(f.already_gone.length) + ' listing(s) were already gone from OnBuy - nothing to do.</p>';
    if (f.errors && f.errors.length) html += '<p class="bad-text">OnBuy errors: ' + f.errors.map((e) => '<code>' + esc(e.sku) + '</code> ' + esc(e.why)).join('; ') + '</p>';
    if (f.nothing) html += '<p class="muted">Nothing to remove.</p>';
    return html;
  }
  async function delCheck() {
    const out = document.getElementById('delCheck');
    show(out, 'Checking ...');
    const data = await post('/api/store/' + delStore() + '/delete/check', delBody());
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, renderCheck(data), 'good');
    return false;
  }
  async function delPlan() {
    const out = document.getElementById('delPlan');
    const body = delBody();
    delPlanned = null; delSync();
    show(out, 'Saving the list and starting the plan ...');
    const data = await post('/api/store/' + delStore() + '/delete/plan', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>Plan</strong> for ' + esc(data.count) + ' SKU(s) <span class="pill risk-read">dry run</span> - list <a href="' + esc(data.list.url) + '" target="_blank" rel="noopener">' + esc(data.list.path.split('/').pop()) + '</a>'
      + (data.held_count || data.on_orders_count ? ' <span class="muted">(' + esc(data.held_count + data.on_orders_count) + ' kept out: hold lists / open orders)</span>' : '');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) {
      html += ' - ' + runLink(data.run);
      show(out, html + ' ' + pill(data.run), 'good');
      pollRun(delStore(), data.run.id, out, html, { render: renderGuarded, after: () => { delPlanned = JSON.stringify(body); delSync(); } });
    } else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }
  async function delApply() {
    const out = document.getElementById('delResult');
    const body = delBody();
    body.confirm = !!document.getElementById('delConfirm').checked;
    show(out, 'Starting ...');
    const data = await post('/api/store/' + delStore() + '/delete/apply', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    delPlanned = null; delSync();                    // another go needs its own plan
    let html = '<strong>Delete for real</strong> started for ' + esc(data.count) + ' SKU(s) <span class="pill risk-danger">live</span>';
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(delStore(), data.run.id, out, html, { render: renderGuarded }); }
    else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }

  // ---- suspended listings: the hand-delete to-do on the Delete page -----------------------------------------------------------
  let suspData = null;
  function suspRender(err) {
    const body = document.getElementById('suspBody'), c = suspData.counts;
    let html = err ? '<p class="bad-text">' + esc(err) + '</p>' : '';
    if (!c.total) { body.innerHTML = html + '<p class="ok-text">No tool has reported a suspended listing in its recent runs.</p>'; return; }
    html += '<p><strong>' + c.waiting + '</strong> waiting for you' + (c.done ? ' <span class="muted">(' + c.done + ' ticked off already)</span>' : '') + '</p>';
    html += '<table class="compact"><tr><th>Done</th><th>SKU</th><th>Title (when a run knew it)</th><th>Last reported</th><th>By / reported by</th></tr>';
    for (const r of suspData.rows) {
      html += '<tr' + (r.done ? ' class="muted"' : '') + '><td><input type="checkbox"' + (r.done ? ' checked' : '')
        + ' onchange="Dash.suspMark(\'' + esc(r.sku) + '\', this.checked)"></td><td><code>' + esc(r.sku) + '</code></td><td>' + esc(r.title || '') + '</td>'
        + '<td>' + (r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.last) + '</a>' : esc(r.last)) + '</td>'
        + '<td>' + esc(r.done ? r.by + ', ' + (r.at || '').slice(0, 10) : r.source) + '</td></tr>';
    }
    html += '</table>';
    if (suspData.waiting_skus.length) {
      html += '<details><summary>The ' + suspData.waiting_skus.length + ' waiting SKU(s) in one box</summary>'
        + '<textarea readonly rows="' + Math.min(8, suspData.waiting_skus.length) + '" onclick="this.select()">' + esc(suspData.waiting_skus.join('\n')) + '</textarea></details>';
    }
    body.innerHTML = html;
  }
  async function loadSuspended() {
    const data = await get('/api/store/' + document.getElementById('suspCard').dataset.store + '/suspended');
    if (data.error) { document.getElementById('suspBody').innerHTML = '<p class="bad-text">' + esc(data.error) + '</p>'; return; }
    suspData = data; suspRender();
  }
  async function suspMark(sku, done) {
    const data = await post('/api/store/' + document.getElementById('suspCard').dataset.store + '/suspended/mark', { sku, done });
    if (data.error) { suspRender(data.error); return; }
    for (const r of suspData.rows) if (r.sku === sku) { r.done = data.done; r.by = 'you'; r.at = new Date().toISOString(); }
    suspData.rows.sort((a, b) => a.done - b.done);                  // stable: the ticked row sinks, the rest keep their order
    suspData.waiting_skus = suspData.rows.filter((r) => !r.done).map((r) => r.sku);
    suspData.counts.done = suspData.rows.length - suspData.waiting_skus.length;
    suspData.counts.waiting = suspData.waiting_skus.length;
    suspRender();
  }
  if (document.getElementById('suspCard')) loadSuspended();

  // ---- buy box card ----
  function bbStore() { return document.getElementById('buybox').dataset.store; }
  const bbNum = (id) => document.getElementById(id).value;
  function renderDefense(f) {
    if (f.off) return '<p class="muted">The Buy Box defense is switched off for the daily run: this run did nothing.</p>';
    const c = f.counts || {};
    let html = '<table class="compact facts">';
    if (f.candidates != null) html += '<tr><td>Listings checked</td><td><strong>' + esc(f.candidates) + '</strong> of ' + esc(f.live) + ' live (in stock, not protected)</td></tr>';
    if (f.share != null) html += '<tr><td>Holding the Buy Box</td><td><strong>' + esc(f.share) + '%</strong> (' + esc(c.winning) + ')</td></tr>';
    if (c.reprice != null) html += '<tr><td>' + (f.dry_run ? 'Would be lowered to win it' : 'Lowered to win it') + '</td><td><strong>' + esc(c.reprice) + '</strong></td></tr>';
    if (c.held != null) html += '<tr><td>Held at the floor</td><td>' + esc(c.held) + ' (the rival is below the floor: never chased)</td></tr>';
    if (c.restored != null) html += '<tr><td>Put back after a contest</td><td>' + esc(c.restored) + '</td></tr>';
    if (c['cheaper-not-winning'] != null) html += '<tr><td>Cheaper, still not winning</td><td>' + esc(c['cheaper-not-winning']) + ' (decided by ratings or delivery)</td></tr>';
    if (c['no cost'] != null) html += '<tr><td>No cost on the sheet</td><td>' + esc(c['no cost']) + ' (never touched)</td></tr>';
    if (c['no data'] != null) html += '<tr><td>No answer from OnBuy</td><td>' + esc(c['no data']) + '</td></tr>';
    if (f.pushed != null) html += '<tr><td>Pushed to OnBuy</td><td><strong>' + esc(f.pushed) + '</strong>' + (f.failed ? ' <span class="bad-text">(' + esc(f.failed) + ' failed)</span>' : '') + '</td></tr>';
    if (f.nothing_pushed) html += '<tr><td>Dry run</td><td>nothing was pushed</td></tr>';
    html += '</table>';
    if (f.pushes && f.pushes.length) html += '<details><summary>Prices ' + (f.dry_run ? 'it would set' : 'lowered') + ' (' + esc(f.pushes.length) + ')</summary><p>' + f.pushes.slice(0, 60).map((p) => '<code>' + esc(p.sku) + '</code> £' + esc(p.price.toFixed(2))).join(' · ') + (f.pushes.length > 60 ? ' ...' : '') + '</p></details>';
    return html;
  }
  async function bbSave() {
    const out = document.getElementById('bbSaved');
    show(out, 'Saving ...');
    const data = await post('/api/store/' + bbStore() + '/buybox/settings', { enabled: document.getElementById('bbEnabled').checked, undercut_pence: bbNum('bbUndercut'), profit_percent: bbNum('bbProfit'),
      confirm: document.getElementById('bbConfirm').checked });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    const s = data.settings;
    show(out, 'Saved: the daily run is <strong>' + (s.enabled ? 'on' : 'off') + '</strong>, undercut <strong>' + esc(s.undercut) + 'p</strong>, floor keeps <strong>' + esc(s.profit) + '%</strong>. They apply from the next daily run.', 'good');
    setTimeout(() => location.reload(), 2500);
    return false;
  }
  async function bbRun(mode) {
    const out = document.getElementById('bbResult');
    show(out, 'Starting ...');
    const body = mode === 'live' ? { mode, confirm: document.getElementById('bbLiveConfirm').checked } : { mode, undercut_pence: bbNum('bbTryUndercut'), profit_percent: bbNum('bbTryProfit') };
    const data = await post('/api/store/' + bbStore() + '/buybox/run', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>Buy Box ' + (mode === 'live' ? 'live run' : 'preview') + '</strong> started ' + (data.live ? '<span class="pill risk-danger">live</span>' : '<span class="pill risk-read">dry run</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(bbStore(), data.run.id, out, html, { render: renderDefense }); }
    else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }

  // ---- amazon card ----
  function amzStore() { return document.getElementById('amazon').dataset.store; }
  function renderCensus(f) {
    if (!f.sellers) return '<p class="muted">The run printed no census (the store has no Amazon tab with a seller column?).</p>';
    let html = '<table class="compact facts"><tr><th>Seller Keepa reported last</th><th>Rows</th><th>With stock</th></tr>';
    for (const s of f.sellers) html += '<tr><td>' + esc(s.seller) + '</td><td>' + esc(s.all.toLocaleString()) + '</td><td>' + esc(s.live.toLocaleString()) + '</td></tr>';
    html += '</table>';
    if (f.would_zero != null) html += '<p>With the strict stock rule <strong>' + esc(f.would_zero.toLocaleString()) + '</strong> of the ' + esc((f.live || 0).toLocaleString()) + ' rows that have stock' + (f.would_zero_share != null ? ' (' + esc(f.would_zero_share) + '%)' : '') + ' would go to stock 0: they are live on a third-party offer only.</p>';
    return html + '<p><a href="" onclick="location.reload();return false">Reload the page to put this in the settings box</a></p>';
  }
  async function amzCensus() {
    await startRun(amzStore(), 'amazon_seller_census.yml', { sample: '15' }, false, document.getElementById('amzCensus'), { render: renderCensus });
    return false;
  }
  async function amzSave() {
    const out = document.getElementById('amzSaved');
    show(out, 'Saving ...');
    const values = {};
    for (const row of document.querySelectorAll('#amzSettings [data-amz-key]')) {
      const input = row.querySelector('input');
      if (!input || input.disabled) continue;
      values[row.dataset.amzKey] = row.dataset.kind === 'switch' ? input.checked : input.value;
    }
    const data = await post('/api/store/' + amzStore() + '/amazon/settings', { values, confirm: document.getElementById('amzConfirm').checked, confirm_strict: document.getElementById('amzStrict').checked });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    const names = Object.keys(data.written || {});
    if (!names.length) { show(out, esc(data.note || 'Nothing changed.'), 'good'); return false; }
    show(out, 'Saved: ' + names.map((n) => '<code>' + esc(n) + '</code> = <strong>' + esc(data.written[n]) + '</strong>').join(' · ') + '. They apply from the next Amazon sync.', 'good');
    setTimeout(() => location.reload(), 2500);
    return false;
  }

  // ---- delivery card ----
  function dtStore() { return document.getElementById('delivery').dataset.store; }
  function renderTemplates(f) {
    let html = '<table class="compact facts">';
    if (f.mode) html += '<tr><td>Mode</td><td><strong>' + esc(f.mode) + '</strong>' + (f.plan_only ? ' (nothing changed)' : '') + '</td></tr>';
    if (f.ids) html += '<tr><td>Template ids used</td><td>' + ['ebay', 'amazon', 'ali'].filter((k) => f.ids[k]).map((k) => esc({ ebay: 'eBay', amazon: 'Amazon', ali: 'AliExpress' }[k]) + ' <code>' + esc(f.ids[k]) + '</code>').join(' · ') + (Object.values(f.ids).some(Boolean) ? '' : 'none set') + '</td></tr>';
    if (f.listings != null) html += '<tr><td>Listings read</td><td><strong>' + esc(f.listings) + '</strong></td></tr>';
    if (f.to_move != null) html += '<tr><td>Off their supplier\'s template</td><td><strong>' + esc(f.to_move) + '</strong>' + (f.priceless != null ? ' (' + esc(f.priceless) + ' never live: no price, cannot be moved)' : '') + '</td></tr>';
    if (f.applied_ok != null) html += '<tr><td>Moved</td><td><strong>' + esc(f.applied_ok) + '</strong> ok' + (f.applied_failed ? ', <span class="bad-text">' + esc(f.applied_failed) + ' failed</span>' : '') + (f.readback ? ' · read-back ' + esc(f.readback.ok) + ' of ' + esc(f.readback.of) + ' already show it' : '') + '</td></tr>';
    if (f.test) html += '<tr><td>Test listing</td><td><code>' + esc(f.test.sku) + '</code> (' + esc(f.test.supplier) + '): template ' + esc(f.test.before) + ' &rarr; wanted ' + esc(f.test.want) + (f.test.after ? ', now ' + esc(f.test.after) : '') + '</td></tr>';
    if (f.result) html += '<tr><td>Result</td><td><strong>' + esc(f.result) + '</strong></td></tr>';
    html += '</table>';
    if (f.classes) html += '<table class="compact"><tr><th>Supplier</th><th>Listings</th><th>Where they sit</th></tr>' + Object.entries(f.classes).map(([k, c]) => '<tr><td>' + esc(k) + '</td><td>' + esc(c.listings) + '</td><td class="muted">' + Object.entries(c.templates).map(([t, n]) => '<code>' + esc(t) + '</code> ' + esc(n)).join(' · ') + '</td></tr>').join('') + '</table>';
    if (f.moves) html += '<p>To move: ' + f.moves.map((m) => '<code>' + esc(m.supplier) + '</code> ' + esc(m.from) + ' &rarr; ' + esc(m.to) + ': <strong>' + esc(m.n) + '</strong>').join(' · ') + '</p>';
    if (f.refused) html += '<p class="bad-text"><strong>Refused:</strong> ' + esc(f.refused.moves) + ' listings would move, above the limit of ' + esc(f.refused.max) + ' - nothing was changed.</p>';
    if (f.semi_warning) html += '<p class="warn-text">' + esc(f.semi_warning) + '</p>';
    return html;
  }
  async function dtSave() {
    const out = document.getElementById('dtSaved');
    show(out, 'Saving ...');
    const body = { confirm: document.getElementById('dtConfirm').checked };
    document.querySelectorAll('#delivery .dtid').forEach((el) => { body[el.dataset.key] = el.value; });
    const data = await post('/api/store/' + dtStore() + '/delivery/settings', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, 'Saved: ' + data.ids.map((i) => esc(i.label) + ' <code>' + esc(i.id || '-') + '</code>').join(' · ') + '. The next run uses them.', 'good');
    setTimeout(() => location.reload(), 2500);
    return false;
  }
  async function dtRun(mode) {
    const out = document.getElementById('dtResult');
    show(out, 'Starting ...');
    const body = { mode };
    if (mode === 'test') { body.test_sku = document.getElementById('dtTestSku').value; body.clear_handling = document.getElementById('dtClear').checked; body.confirm = document.getElementById('dtRunConfirm').checked; }
    if (mode === 'apply') { body.max_changes = document.getElementById('dtMax').value; body.clear_handling = document.getElementById('dtClear').checked; body.confirm = document.getElementById('dtRunConfirm').checked; }
    const data = await post('/api/store/' + dtStore() + '/delivery/run', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>Delivery ' + esc(mode) + '</strong> started ' + (data.live ? '<span class="pill risk-danger">live</span>' : '<span class="pill risk-read">read only</span>');
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) { html += ' - ' + runLink(data.run); show(out, html + ' ' + pill(data.run), 'good'); pollRun(dtStore(), data.run.id, out, html, { render: renderTemplates, reload: mode === 'plan' }); }
    else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }

  // ---- pictures card ----
  function picStore() { return document.getElementById('pictures').dataset.store; }
  function picRemember(key, value) {
    // the two names of the reply draft are kept in this browser; a private window just forgets them
    try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { /* not remembered */ }
    return null;
  }
  function picSync() {
    const typed = document.getElementById('picSkus').value.split(/[,\s]+/).filter(Boolean);
    const unique = new Set(typed).size;
    document.getElementById('picCount').textContent = unique + ' SKU' + (unique === 1 ? '' : 's') + (typed.length > unique ? ' (' + (typed.length - unique) + ' repeated)' : '');
  }
  function picFile(input) {
    // the browser scan's own CSV is read on the server: only the stuck products go in the box; any other file keeps the old reading (first column)
    const file = input.files && input.files[0];
    if (!file) return;
    const note = document.getElementById('picScanNote');
    const say = (text, cls) => { if (note) { note.textContent = text; note.className = 'hint ' + (cls || ''); } };
    const reader = new FileReader();
    reader.onload = async () => {
      say('Reading ' + file.name + ' ...');
      const data = await post('/api/store/' + picStore() + '/pictures/scan', { text: String(reader.result) });
      input.value = '';
      if (data.error) { say(file.name + ': ' + data.error, 'bad-text'); return; }
      const box = document.getElementById('picSkus');
      if (data.scan) {
        box.value = (data.stuck || []).join('\n');
        const why = Object.entries(data.why || {}).map(([k, v]) => v + ' × ' + k).join(', ');
        let text = file.name + ': ' + data.total + ' scanned - ' + (data.stuck || []).length + ' stuck' + (why ? ' (' + why + ')' : '') + ' are in the box, ' + data.fine + ' fine left out';
        if (data.unclear) text += '; ' + data.unclear + ' the scan could not see - scan those again';
        if (data.over) text += '. That is more than one build takes: build the ticket in parts.';
        say(text + '.', (data.stuck || []).length ? 'warn-text' : 'ok-text');
      } else {
        box.value = (data.skus || []).join('\n');
        say(file.name + ': ' + data.count + ' SKU(s) read - not a scan file, so the first column was taken as it is.');
      }
      picSync();
    };
    reader.readAsText(file);
  }
  async function picLast() {
    // the next ticket usually means "everything from last time plus the new pastes": fill the box with the last build's full list, then paste on top
    const note = document.getElementById('picScanNote');
    const data = await get('/api/store/' + picStore() + '/pictures/last_skus');
    if (data.error) { if (note) { note.textContent = data.error; note.className = 'hint bad-text'; } return false; }
    const box = document.getElementById('picSkus');
    box.value = (data.skus || []).join('\n') + '\n';
    if (note) { note.textContent = 'The last ticket’s ' + (data.skus || []).length + ' SKU(s) (' + data.day + ') are in the box - paste the new ones underneath.'; note.className = 'hint'; }
    box.focus();
    box.setSelectionRange(box.value.length, box.value.length);
    picSync();
    return false;
  }
  function renderJob(v) {
    const steps = v.steps || [];
    const head = v.state === 'failed' ? 'The build stopped' : (v.state === 'done' ? 'Done' : 'Building the ticket');
    let html = '<strong>' + head + '</strong> <span class="muted">(' + Math.round(v.seconds) + ' s)</span>';
    if (v.state === 'failed') html += '<br><span class="bad-text">' + esc(v.error) + '</span><br><span class="muted">Nothing was changed on OnBuy. Fix the cause and press Build the ticket again.</span>';
    html += '<ol class="steps">' + steps.map((s, i) => {
      if (i < steps.length - 1 || v.state === 'done') return '<li>' + esc(s.text) + ' <span class="ok-text">done</span></li>';
      if (v.state === 'failed') return '<li>' + esc(s.text) + ' <span class="bad-text">stopped here</span></li>';
      return '<li><strong>' + esc(s.text) + '</strong> ...' + (v.total ? ' ' + esc(v.done) + ' of ' + esc(v.total) : '') + (v.detail ? ' <span class="muted">' + esc(v.detail) + '</span>' : '') + '</li>';
    }).join('') + '</ol>';
    return html;
  }
  async function picWatch(jobId) {
    const out = document.getElementById('picJob');
    const btn = document.getElementById('picBuild');
    btn.disabled = true;
    for (let i = 0; i < 1500; i++) {                                // about 75 minutes at one look every 3 s
      const v = await get('/api/store/' + picStore() + '/pictures/job/' + jobId);
      if (v.error) { show(out, esc(v.error), 'bad'); btn.disabled = false; return; }
      show(out, renderJob(v), v.state === 'failed' ? 'bad' : 'good');
      if (v.state === 'done') { setTimeout(() => location.reload(), 800); return; }
      if (v.state === 'failed') { btn.disabled = false; return; }
      await new Promise((r) => setTimeout(r, 3000));
    }
    show(out, 'Still running after 75 minutes - reload the page to see where it is.', 'bad');
  }
  async function picBuild() {
    const out = document.getElementById('picJob');
    const agent = document.getElementById('picAgent').value, signed = document.getElementById('picSigned').value;
    picRemember('pic_agent', agent); picRemember('pic_signed', signed);
    show(out, 'Starting ...');
    const data = await post('/api/store/' + picStore() + '/pictures/ticket', { skus: document.getElementById('picSkus').value, agent, signed_by: signed });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    picWatch(data.job.id);
    return false;
  }
  async function picCopy() {
    const box = document.getElementById('picReply'), note = document.getElementById('picCopied');
    try { await navigator.clipboard.writeText(box.value); note.textContent = 'Copied.'; }
    catch (e) { box.select(); note.textContent = (document.execCommand && document.execCommand('copy')) ? 'Copied.' : 'Select the text and copy it yourself.'; }
    return false;
  }
  function renderRepair(f) {
    let html = '<table class="compact facts">';
    if (f.worksheet) html += '<tr><td>Sheet tab</td><td><strong>' + esc(f.worksheet) + '</strong></td></tr>';
    if (f.live != null) html += '<tr><td>Live listings read</td><td>' + esc(f.live) + '</td></tr>';
    if (f.repairable != null) html += '<tr><td>Products that qualify</td><td><strong>' + esc(f.repairable) + '</strong>' + (f.skipped_incomplete ? ' <span class="muted">(+' + esc(f.skipped_incomplete) + ' skipped: no category or main picture on the sheet)</span>' : '') + '</td></tr>';
    if (f.limit != null) html += '<tr><td>Limit of this run</td><td>' + esc(f.limit) + '</td></tr>';
    if (f.submitted != null) html += '<tr><td>Resubmitted</td><td><strong>' + esc(f.submitted) + '</strong> ok' + (f.failed_count ? ', <span class="bad-text">' + esc(f.failed_count) + ' failed</span>' : '') + '</td></tr>';
    if (f.dry_run) html += '<tr><td>Dry run</td><td>nothing was sent to OnBuy</td></tr>';
    html += '</table>';
    if (f.rate_limited) html += '<p class="warn-text"><strong>OnBuy\'s rate limit stopped the run.</strong> Wait a few minutes and press the button again: it continues with what is left.</p>';
    if (f.targets && f.targets.length) {
      html += '<details' + (f.dry_run ? ' open' : '') + '><summary>' + (f.dry_run ? 'Would be resubmitted' : 'Resubmitted or tried') + ' (' + esc(f.targets.length) + ') - what OnBuy shows for them today</summary>'
        + '<table class="compact"><tr><th>SKU</th><th>OnBuy shows</th></tr>' + f.targets.slice(0, 60).map((t) => '<tr><td><code>' + esc(t.sku) + '</code></td><td class="muted">' + esc(t.shows) + '</td></tr>').join('') + '</table>'
        + (f.targets.length > 60 ? '<p class="muted">... and ' + (f.targets.length - 60) + ' more</p>' : '') + '</details>';
    }
    if (f.failed && f.failed.length) html += '<p class="bad-text"><strong>Failed:</strong> ' + f.failed.slice(0, 30).map((x) => '<code>' + esc(x.sku) + '</code> ' + esc(x.why)).join('; ') + '</p>';
    if (f.collisions && f.collisions.length) html += '<p class="muted">' + esc(f.collisions.length) + ' barcode collision(s) are only reported, never touched.</p>';
    return html;
  }
  async function picResub(tab, mode) {
    const out = document.getElementById('picResubResult');
    show(out, 'Starting ...');
    const data = await post('/api/store/' + picStore() + '/pictures/resubmit', { tab, mode, confirm: !!document.getElementById('picConfirm').checked });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    let html = '<strong>Resubmission</strong> of up to ' + esc(data.count) + ' product(s), tab ' + esc(data.tab) + ' ' + (mode === 'preview' ? '<span class="pill risk-read">dry run</span>' : '<span class="pill risk-danger">live</span>' + (mode === 'canary' ? ' the first ' + esc(document.getElementById('pictures').dataset.canary) : ''));
    if (data.warning) html += ' <span class="muted">' + esc(data.warning) + '</span>';
    if (data.run) {
      html += ' - ' + runLink(data.run);
      show(out, html + ' ' + pill(data.run), 'good');
      pollRun(picStore(), data.run.id, out, html, { render: renderRepair, after: () => { if (mode !== 'preview') out.insertAdjacentHTML('beforeend', '<p><a href="" onclick="location.reload();return false">Reload the page to update the counts</a></p>'); } });
    } else show(out, html + ' - GitHub has not listed the run yet.', 'good');
    return false;
  }
  function picInit() {
    const agent = picRemember('pic_agent'), signed = picRemember('pic_signed');
    if (agent) document.getElementById('picAgent').value = agent;
    if (signed) document.getElementById('picSigned').value = signed;
    picSync();
    const running = document.getElementById('pictures').dataset.job;
    if (running) picWatch(running);                                 // a build started before this page was opened goes on being followed
  }
  if (document.getElementById('pictures')) picInit();

  // ---- the home page's "Needs you today" band --------------------------------------------------------------------------------
  async function loadTodoBand() {
    const body = document.getElementById('todoBandBody');
    const data = await get('/api/todo/summary');
    if (data.error) { body.innerHTML = '<span class="bad-text">' + esc(data.error) + '</span>'; return; }
    body.innerHTML = (data.stores || []).map((s) => {
      let right;
      if (s.error) right = '<span class="bad-text">could not be read: ' + esc(s.error).slice(0, 90) + '</span>';
      else if (!s.counts.total) right = '<span class="pill ok">all clear</span>';
      else {
        const parts = [];
        if (s.counts.act) parts.push('<span class="pill failed">' + esc(s.counts.act) + ' act now</span>');
        if (s.counts.look) parts.push('<span class="pill stale">' + esc(s.counts.look) + ' look today</span>');
        if (s.counts.fyi) parts.push('<span class="pill quiet">' + esc(s.counts.fyi) + ' fyi</span>');
        right = parts.join(' ') + ' <span class="muted">' + (s.top || []).map((t) => esc(t.title)).join(' &middot; ') + '</span>';
      }
      return '<div class="bandrow"><a class="chip" href="/todo#' + esc(s.store) + '">' + esc(s.name) + '</a><div>' + right + '</div></div>';
    }).join('');
    const at = document.getElementById('todoBandAt');
    if (at && data.at) at.textContent = 'checked ' + new Date(data.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (document.getElementById('todoBand')) loadTodoBand();

  // ---- the Daily check page's "Rows that keep failing" card -------------------------------------------------------------------
  function problemsStore(s) {
    if (!s.kinds.length) return '';
    const perNight = (s.nights || []).map((n) => '<a href="' + esc(n.url) + '" target="_blank" rel="noopener" title="' + esc(n.day) + '">' + (n.fix + n.bounce + n.suspended) + '</a>').join(' &middot; ');
    let html = '<h3><a href="/store/' + esc(s.store) + '">' + esc(s.name) + '</a> <small class="muted">refusals per night, newest first: ' + perNight + '</small></h3>';
    html += '<table class="compact"><tr><th>What OnBuy refused</th><th>Last night</th><th>On 2+ nights</th><th>One night only</th></tr>';
    for (const k of s.kinds) {
      html += '<tr><td>' + esc(k.label) + (k.reason ? ' <span class="muted">- "' + esc(k.reason) + '"</span>' : '') + '</td><td><strong>' + k.latest + '</strong></td>'
        + '<td class="' + (k.repeat_count ? 'bad-text' : '') + '"><strong>' + k.repeat_count + '</strong>' + (k.most_nights > 2 ? ' <span class="muted">(up to ' + k.most_nights + ' nights)</span>' : '') + '</td><td>' + k.once_count + '</td></tr>';
    }
    html += '</table>';
    for (const k of s.kinds) {
      if (!k.skus.length) continue;
      html += '<details><summary>' + esc(k.skus_label) + ' (' + k.skus.length + ')</summary><p class="hint">' + esc(k.note) + '</p>'
        + '<textarea readonly rows="' + Math.min(8, k.skus.length) + '" onclick="this.select()">' + esc(k.skus.join('\n')) + '</textarea></details>';
    }
    return html;
  }
  async function loadProblems() {
    const body = document.getElementById('problemsBody');
    const data = await get('/api/problems');
    if (data.error) { body.innerHTML = '<p class="bad-text">' + esc(data.error) + '</p>'; return; }
    const stores = data.stores || [];
    const blocks = stores.map(problemsStore).filter(Boolean);
    const clear = stores.filter((s) => !s.error && !s.kinds.length).map((s) => esc(s.name) + ' <span class="muted">(' + s.nights.length + ' night(s) read)</span>');
    const errors = stores.filter((s) => s.error).map((s) => esc(s.name) + ' could not be read: ' + esc(s.error).slice(0, 90));
    body.innerHTML = (blocks.length ? blocks.join('') : '<p class="ok-text">No refusals in the nights read: nothing kept failing.</p>')
      + (clear.length && blocks.length ? '<p class="muted">Nothing refused on ' + clear.join(', ') + '.</p>' : '')
      + (errors.length ? '<p class="bad-text">' + errors.join('<br>') + '</p>' : '');
  }
  if (document.getElementById('problemsCard')) loadProblems();

  // ---- orphans (Catalogue) ----
  function orphStore() { const el = document.getElementById('catalogue'); return el ? el.dataset.store : ''; }
  async function loadOrphans(refresh) {
    const box = document.getElementById('orphans');
    if (!box) return false;
    box.innerHTML = '<p class="muted">Reading the latest scan ...</p>';
    const data = await get('/api/store/' + orphStore() + '/orphans' + (refresh ? '?refresh=1' : ''));
    if (data.error) { box.innerHTML = '<p class="muted">' + esc(data.error) + '</p>'; return false; }
    const rows = data.rows || [];
    if (!rows.length) { box.innerHTML = '<p class="ok-text">No orphans: every live listing sits on a sheet row.</p>'; return false; }
    let html = '<p><strong>' + data.count + '</strong> live listing(s) on no sheet row - <strong>' + data.in_stock + '</strong> in stock right now, sellable at a price nothing refreshes. '
      + 'From <a href="' + esc(data.run.url) + '" target="_blank" rel="noopener">the scan of ' + esc(data.run.when) + '</a>'
      + ' - <a href="#" onclick="return Dash.loadOrphans(1)">read again</a> - <a href="/api/store/' + orphStore() + '/orphans.csv">download every row as CSV</a>.</p>';
    html += '<table class="compact"><tr><th>SKU</th><th>Price</th><th>Stock</th><th>Created</th><th>Listing</th></tr>';
    for (const r of rows.slice(0, 60)) {
      html += '<tr><td><code>' + esc(r.sku) + '</code></td><td>' + r.price.toFixed(2) + '</td><td>' + (r.stock > 0 ? '<strong>' + r.stock + '</strong>' : r.stock) + '</td><td class="muted">' + esc(r.created) + '</td><td>' + esc(r.title) + '</td></tr>';
    }
    html += '</table>';
    if (data.count > 60) html += '<p class="muted">Showing the first 60 of ' + data.count + (data.truncated ? ' (the answer carries ' + rows.length + ')' : '') + ' - the CSV has every one.</p>';
    html += '<details><summary>SKUs paste-ready (' + rows.length + ')</summary><p class="hint">One per line, in-stock first - for the Delete page\'s delete-by-list, or a ticket.</p>'
      + '<textarea readonly rows="8" onclick="this.select()">' + esc(rows.map((r) => r.sku).join('\n')) + '</textarea></details>';
    box.innerHTML = html;
    return false;
  }
  if (document.getElementById('orphansCard')) loadOrphans();

  // ---- sheet health (store page) ----
  async function loadSheetHealth() {
    const box = document.getElementById('sheethealth');
    const cardEl = document.getElementById('sheetCard');
    if (!box || !cardEl) return false;
    const data = await get('/api/store/' + cardEl.dataset.store + '/sheet');
    if (data.error) { box.innerHTML = '<p class="muted">' + esc(data.error) + '</p>'; return false; }
    let html = '';
    for (const [tab, label] of [['ebay', 'eBay tab'], ['amazon', 'Amazon tab']]) {
      const d = data[tab];
      if (!d) continue;
      html += '<h3>' + label + (d.run ? ' <a class="muted" href="' + esc(d.run.url) + '" target="_blank" rel="noopener">' + esc(d.run.when) + '</a>' : '') + '</h3>';
      if (d.missing) { html += '<p class="muted">' + esc(d.missing) + '</p>'; continue; }
      if (d.issues && d.issues.length) {
        html += '<p>' + d.issues.map(([name, n, cls]) => '<span class="pill ' + (cls === 'bad' ? 'failed' : cls === 'warn' ? 'stale' : 'quiet') + '">' + n + ' ' + esc(name) + '</span>').join(' ') + '</p>';
      } else {
        html += '<p><span class="pill ok">nothing held back</span></p>';
      }
      const facts = [['rows', 'Rows'], ['processable', 'Processable'], ['unfilled', 'Unfilled'], ['created', 'Created last run'], ['brand_blocked', 'Brand-blocked']];
      html += '<table class="facts compact">' + facts.filter(([k]) => d[k] !== undefined)
        .map(([k, lab]) => '<tr><td>' + lab + '</td><td><strong>' + d[k] + '</strong></td></tr>').join('') + '</table>';
      if (d.no_sku && d.no_sku.count) {
        html += '<p class="warn-text">' + d.no_sku.count + ' row(s) wait for a SKU' + (d.no_sku.sample_rows.length ? ' <span class="muted">(sheet rows ' + d.no_sku.sample_rows.join(', ') + (d.no_sku.count > d.no_sku.sample_rows.length ? ', ...' : '') + ')</span>' : '') + '</p>';
      }
      if (d.duplicate_links) {
        html += '<table class="compact"><tr><th>Row</th><th>SKU</th><th>Same supplier item as</th></tr>' + d.duplicate_links.map((x) =>
          '<tr><td>' + x.row + '</td><td><code>' + esc(x.sku) + '</code></td><td>row ' + x.original_row + '</td></tr>').join('') + '</table>';
      }
    }
    box.innerHTML = html || '<p class="muted">No finished sync yet.</p>';
    return false;
  }
  if (document.getElementById('sheetCard')) loadSheetHealth();

  // ---- creations in flight (store page) ----
  async function loadCreations() {
    const box = document.getElementById('creations');
    const cardEl = document.getElementById('sheetCard');
    if (!box || !cardEl) return false;
    const data = await get('/api/store/' + cardEl.dataset.store + '/creations');
    if (data.error || data.missing) { box.innerHTML = '<p class="muted">' + esc(data.error || data.missing) + '</p>'; return false; }
    let html = '';
    const pend = data.pending || {};
    const o = data.outcomes || {};
    const pills = [];
    if (pend.ebay) pills.push('<span class="pill stale">' + pend.ebay + ' eBay waiting</span>');
    if (pend.amazon) pills.push('<span class="pill stale">' + pend.amazon + ' Amazon waiting</span>');
    if (o.success) pills.push('<span class="pill ok">' + o.success + ' got their OPC</span>');
    for (const [k, n] of Object.entries(o)) if (k !== 'success') pills.push('<span class="pill failed">' + n + ' ' + esc(k) + '</span>');
    if (!pills.length) pills.push('<span class="pill ok">nothing in flight</span>');
    html += '<p>' + pills.join(' ') + ' <a class="muted" href="' + esc(data.run.url) + '" target="_blank" rel="noopener">' + esc(data.run.when) + '</a></p>';
    const facts = [];
    if (data.listings_live !== undefined) facts.push(['Listings live on OnBuy', data.listings_live]);
    if (data.queue_found !== undefined) facts.push(['Answered by the queue', data.queue_found + ' of ' + data.queue_checked]);
    for (const f of data.opc_fill || []) facts.push(['Blank OPCs filled (' + f.tab + ')', f.filled + (f.unlisted ? ' (' + f.unlisted + ' not listed by OnBuy)' : '')]);
    if (facts.length) html += '<table class="facts compact">' + facts.map(([k, v]) => '<tr><td>' + k + '</td><td><strong>' + v + '</strong></td></tr>').join('') + '</table>';
    if (data.failures) {
      html += '<table class="compact"><tr><th>SKU</th><th>Status</th><th>OnBuy\'s reason</th></tr>' + data.failures.map((f) =>
        '<tr><td><code>' + esc(f.sku) + '</code></td><td><span class="pill failed">' + esc(f.status) + '</span></td><td class="muted">' + esc(f.reason) + '</td></tr>').join('') + '</table>';
    }
    box.innerHTML = html;
    return false;
  }
  if (document.getElementById('creations')) loadCreations();

  // ---- the Amazon schedule (Amazon page) ----
  const num = (n) => (n === undefined || n === null) ? '-' : Number(n).toLocaleString('en-GB');
  async function loadSchedule(refresh) {
    const box = document.getElementById('schedBody');
    if (!box) return false;
    box.innerHTML = '<p class="muted">Reading the dispatchers ...</p>';
    const data = await get('/api/amazon/schedule' + (refresh ? '?refresh=1' : ''));
    if (data.error) { box.innerHTML = '<p class="muted">' + esc(data.error) + '</p>'; return false; }
    const rows = data.stores || [];
    let html = '<table class="compact"><tr><th>Account</th><th>Amazon products</th><th>Runs a day</th><th>Products per run</th><th>Products a day</th><th>A product refreshed every</th><th>Keepa tokens a day</th><th>Syncs, last 24 h</th><th>Latest decision</th></tr>';
    let planned = 0, perDay = 0;
    for (const r of rows) {
      const name = esc(r.store.name);
      if (!r.on_plan) {
        html += '<tr><td><strong>' + name + '</strong></td><td colspan="6" class="muted">on its own fixed cron - ' + esc(r.note || 'no dispatcher yet') + '</td><td>' + num(r.syncs_24h) + '</td><td class="muted">-</td></tr>';
        continue;
      }
      planned += 1; perDay += r.daily || 0;
      const warn = (r.warnings || []).map((w) => '<br><span class="pill stale">' + esc(w) + '</span>').join('');
      const tick = r.last_tick ? ' <a class="muted" href="' + esc(r.last_tick.url) + '" target="_blank" rel="noopener">' + esc(r.last_tick.when) + '</a>' : '';
      const state = r.dispatched ? '<span class="pill ok">launched a sync</span> ' : '<span class="pill quiet">not due</span> ';
      html += '<tr><td><strong>' + name + '</strong>' + warn + '</td><td>' + num(r.n) + '</td><td><strong>' + num(r.runs) + '</strong> <span class="muted">(every ' + (r.runs ? (24 / r.runs).toFixed(r.runs > 6 ? 0 : 1).replace(/\.0$/, '') : '-') + ' h)</span></td>'
        + '<td>' + num(r.slice) + '</td><td><strong>' + num(r.daily) + '</strong></td><td>' + (r.refresh_hours === null || r.refresh_hours === undefined ? '-' : r.refresh_hours + ' h') + '</td>'
        + '<td>' + num(r.tokens_day) + ' <span class="muted">' + (r.share_percent === null || r.share_percent === undefined ? '' : r.share_percent + '% of its ' + num(r.share)) + '</span></td>'
        + '<td>' + num(r.syncs_24h) + '</td><td>' + state + '<span class="muted">' + esc(r.decision || '') + '</span>' + tick + '</td></tr>';
    }
    html += '</table>';
    if (planned) html += '<p><strong>' + num(perDay) + '</strong> Amazon products are refreshed a day across the ' + planned + ' account(s) on the plan. <a href="#" onclick="return Dash.loadSchedule(1)">read again</a></p>';
    box.innerHTML = html;
    return false;
  }
  if (document.getElementById('schedCard')) loadSchedule();

  // ---- the store registry (Settings) -----------------------------------------------------------------------------------------
  async function storeAdd() {
    const out = document.getElementById('stResult');
    const body = { id: document.getElementById('stId').value, name: document.getElementById('stName').value, repo: document.getElementById('stRepo').value,
                   sheet: document.getElementById('stSheet').value, sheet_url: (document.getElementById('stSheetUrl') || { value: '' }).value,
                   product_tab: document.getElementById('stTab').value, amazon_tab: document.getElementById('stAmazonTab').value };
    show(out, 'Checking the repository ...');
    const data = await post('/api/stores', body);
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, '<strong>' + esc(data.store.name) + '</strong> added - every page now carries its chip. <a href="/store/' + esc(data.store.id) + '">Open its store page</a> or <a href="" onclick="location.reload();return false">reload</a>.', 'good');
    return false;
  }
  async function storeRemove(id, name) {
    if (!window.confirm('Remove "' + name + '" from this dashboard? The store itself keeps running untouched - every page just loses its chip.')) return false;
    const out = document.getElementById('stResult');
    const data = await post('/api/stores/' + id + '/remove', { confirm: true });
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, esc(name) + ' removed from the dashboard. <a href="" onclick="location.reload();return false">Reload to see the list</a>.', 'good');
    return false;
  }

  // ---- repository secrets (Settings) -----------------------------------------------------------------------------------------
  let secStore = null, secStoreName = '';
  async function loadSecrets(id, name) {
    secStore = id; secStoreName = name;
    const box = document.getElementById('secrets');
    box.innerHTML = '<p class="muted">Reading ' + esc(name) + "'s secret names ...</p>";
    const data = await get('/api/stores/' + id + '/secrets');
    if (data.error) { box.innerHTML = '<p class="bad-text">' + esc(data.error) + '</p>'; return false; }
    let html = '<h3>' + esc(name) + ' <small class="muted">' + esc(data.repo) + '</small></h3>';
    html += '<table class="compact"><tr><th>Secret</th><th>Last set</th></tr>';
    for (const s of data.secrets) html += '<tr><td><code>' + esc(s.name) + '</code></td><td class="muted">' + esc((s.updated_at || '').slice(0, 10)) + '</td></tr>';
    if (!data.secrets.length) html += '<tr><td colspan="2" class="muted">none yet</td></tr>';
    html += '</table>';
    if (data.missing.length) html += '<p class="warn-text">Still missing the usual: ' + data.missing.map((n) => '<code>' + esc(n) + '</code>').join(' ') + '</p>';
    else html += '<p class="ok-text">Every usual secret is set.</p>';
    html += '<div class="grid two"><label class="stack">Name <input type="text" id="secName" placeholder="ONBUY_CONSUMER_KEY" list="secNames"></label>'
      + '<label class="stack">Value <span class="muted">(sent sealed, never shown again)</span><textarea id="secValue" rows="2"></textarea></label></div>'
      + '<datalist id="secNames">' + (data.missing.concat(data.secrets.map((s) => s.name))).map((n) => '<option value="' + esc(n) + '">').join('') + '</datalist>'
      + '<div class="runctl"><button type="button" onclick="return Dash.secretSet()">Set the secret</button></div><div class="result" id="secResult" hidden></div>';
    box.innerHTML = html;
    return false;
  }
  async function secretSet() {
    const out = document.getElementById('secResult');
    const nameBox = document.getElementById('secName'), valueBox = document.getElementById('secValue');
    const data = await post('/api/stores/' + secStore + '/secrets', { name: nameBox.value, value: valueBox.value });
    valueBox.value = '';                                               // the value never lingers in the page either
    if (data.error) { show(out, esc(data.error), 'bad'); return false; }
    show(out, '<code>' + esc(data.name) + '</code> set - the repository\'s next runs use it. <a href="#" onclick="return Dash.secretsReload()">Reload the list</a>.', 'good');
    return false;
  }
  function secretsReload() { return loadSecrets(secStore, secStoreName); }

  // ---- employees (Settings) ------------------------------------------------------------------------------------------------
  function empOut() { return document.getElementById('empResult'); }
  async function empAdd() {
    const name = document.getElementById('empName').value, role = document.getElementById('empRole').value;
    const data = await post('/api/employees', { name, role });
    if (data.error) { show(empOut(), esc(data.error), 'bad'); return false; }
    show(empOut(), '<strong>' + esc(data.employee.name) + '</strong> added as ' + esc(data.employee.role) + '. Their code is <code>' + esc(data.code)
      + '</code> - <strong>shown only this once</strong>: write it down and hand it over yourself. <a href="" onclick="location.reload();return false">Reload to see the list</a>.', 'good');
    return false;
  }
  async function empSet(id, changes) {
    const data = await post('/api/employees/' + id, changes);
    if (data.error) { show(empOut(), esc(data.error), 'bad'); return false; }
    location.reload();
    return false;
  }
  async function empCode(id, name) {
    const data = await post('/api/employees/' + id + '/code', {});
    if (data.error) { show(empOut(), esc(data.error), 'bad'); return false; }
    show(empOut(), 'New code for <strong>' + esc(name) + '</strong>: <code>' + esc(data.code) + '</code> - <strong>shown only this once</strong>; the old code stopped working now.', 'good');
    return false;
  }
  async function empDel(id, name) {
    const data = await post('/api/employees/' + id + '/delete', {});
    if (data.error) { show(empOut(), esc(data.error), 'bad'); return false; }
    show(empOut(), '<strong>' + esc(name) + '</strong> removed: their code does not sign in any more. <a href="" onclick="location.reload();return false">Reload</a>.', 'good');
    return false;
  }

  window.Dash = { amzSave, amzCensus, picSync, picFile, picBuild, picCopy, picResub, picLast, dtSave, dtRun, bbSave, bbRun, delSync, delFile, delCheck, delPlan, delApply, suspMark, catRelease, catDelete, catForget, catFreeze, catPurge, saleAdd, saleRemove, saleReset, saleFill, salePreview, saleApply, saleTest, saleCancel, runFromForm, openTool, loadVariables, saveVariable, addBand, addWindow, removeBand, calc, pricingPreview, pricingApply, pricingPush, saveFeeMode, empAdd, empSet, empCode, empDel, storeAdd, storeRemove, loadSecrets, secretSet, secretsReload, loadReadiness, rdAdopt, rdWorkflow, loadOrphans, loadSchedule };

  // The "Guide" chip: the explanation text (hints, button notes) is hidden for a compact page; one click brings it back everywhere.
  const guide = document.getElementById('helpToggle');
  if (guide) {
    const sync = () => guide.classList.toggle('on', document.documentElement.classList.contains('explain'));
    sync();
    guide.addEventListener('click', (e) => {
      e.preventDefault();
      const on = document.documentElement.classList.toggle('explain');
      try { localStorage.setItem('dashGuide', on ? '1' : '0'); } catch (err) { /* private mode: the choice just does not stick */ }
      sync();
    });
  }
})();
