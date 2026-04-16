const state = {
  league: 'huracan',
  preGroup: 'B',
  tab: { mini: 'cal', pre: 'cal' },
  idx: { mini: 0, pre: 0 },
  data: { mini: null, pre: null, huracan: null, meta: null },
};

const STATUS = { 1: 'Pendiente', 5: 'Programado', 10: 'Descansa', 20: 'Finalizado' };
const BYE_NAME = 'Descansa';

const LOGOS = {
  'ACODETTI CF': 'acodetti.png',
  'AD HURACAN': 'huracan.png',
  'ATL. GRAN CANARIA': 'atleticograncanaria19-20.png',
  'ATLÉTICO ISLETA': 'isletaEscudo.png',
  'C. D. SAN LAZARO': 'sanlazaro.png',
  'U.D. SAN LAZARO': 'sanlazaro.png',
  'C.D HEIDELBERG': 'heidelberg.png',
  'C.F. UNION VIERA A': 'unionviera.png',
  'C.F. UNION VIERA B': 'unionviera.png',
  'C.F. UNION VIERA C': 'unionviera.png',
  'CD GUINIGUADA APOLINARIO': 'guiniguada2016.png',
  'FUNDACIÓN CANARIA GUINIGUADA': 'guiniguada2016.png',
  'CD LOMO BLANCO': 'lomoblanco.png',
  'CF VETERANOS DEL PILAR A': 'interPilar.png',
  'CF VETERANOS DEL PILAR': 'interPilar.png',
  'VETERANOS DEL PILAR  B': 'interPilar.png',
  'VETERANOS DEL PILAR  C': 'interPilar.png',
  'VETERANOS DEL PILAR D': 'interPilar.png',
  'CORAZÓN DE MARÍA A': 'claret.png',
  'CORAZÓN DE MARÍA B': 'claret.png',
  'CORAZÓN DE MARÍA C': 'claret.png',
  'CORAZÓN DE MARÍA D': 'claret.png',
  'REAL CLUB VICTORIA': 'victoria.png',
  'REAL SPORTING SAN JOSE': 'sportingEscudo2025.png',
  'U.D. PEDRO HIDALGO': 'pedrohidalgo.png',
  'UD LAS PALMAS A': 'lasPalmasEscudo.png',
  'UD LAS PALMAS B': 'lasPalmasEscudo.png',
  'UD LAS PALMAS C': 'lasPalmasEscudo.png',
  'UD LAS PALMAS D': 'lasPalmasEscudo.png',
  'UD LAS PALMAS E': 'lasPalmasEscudo.png',
  'UD LAS PALMAS F': 'lasPalmasEscudo.png',
  'UD TAMARACEITE': 'tamaraceite.png',
  'ARBOL BONITO MIGUEL LEON': 'arbolbonito.jpg',
  'INTER CANARIAS': 'intercanarias.jpg',
};

function logoFor(name) {
  if (!name) return null;
  const key = name.toUpperCase().trim();
  return LOGOS[key] || null;
}

function avatarHTML(cls, name) {
  const logo = logoFor(name);
  if (logo) {
    return `<div class="${cls} has-logo"><img src="./logos/${logo}" alt="${esc(name)}" loading="lazy"/></div>`;
  }
  return `<div class="${cls}">${esc(initials(name))}</div>`;
}

const $ = (id) => document.getElementById(id);

const esc = (s) => String(s ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

const initials = (n) =>
  (n.split(/\s+/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase() || 'EQ');

function fmtDate(v) {
  if (!v) return 'Sin fecha';
  try {
    return new Date(v).toLocaleString('es-ES', {
      weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return v;
  }
}

function isPlayed(m) {
  return m.status === 20;
}

function isFuture(m) {
  if (!m.date) return false;
  const ts = Date.parse(m.date);
  return !Number.isNaN(ts) && ts >= Date.now();
}

function teamName(kind, id) {
  if (id === -1) return BYE_NAME;
  const teams = state.data[kind]?.teams || {};
  if (kind === 'mini') return teams[id] || `#${id}`;
  return teams[id]?.name || `#${id}`;
}

function teamGroup(kind, id) {
  if (kind !== 'pre') return '-';
  return state.data.pre?.teams?.[id]?.group || 'A';
}

function getJornadas(kind) {
  const jornadas = state.data[kind]?.jornadas || [];
  if (kind !== 'pre') return jornadas;
  return jornadas.filter((j) => (j.matches || []).some((m) => {
    const home = state.data.pre?.teams?.[m.home];
    const away = state.data.pre?.teams?.[m.away];
    return (home?.group || away?.group || 'A') === state.preGroup;
  }));
}

function getMatches(kind, jornada) {
  if (!jornada) return [];
  let matches = jornada.matches || [];
  if (kind === 'pre') {
    matches = matches.filter((m) => {
      const home = state.data.pre?.teams?.[m.home];
      const away = state.data.pre?.teams?.[m.away];
      return (home?.group || away?.group || 'A') === state.preGroup;
    });
  }
  return matches;
}

function renderHeaders() {
  const meta = state.data.meta;
  if (!meta) return;
  const mini = meta.leagues.mini;
  const pre = meta.leagues.pre;
  const season = meta.season || '2025 / 2026';

  const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };
  setText('nav-season', `Temporada ${season}`);
  setText('lhdr-mini-meta', `${mini.teams} equipos · ${mini.jornadas} jornadas`);

  const groups = pre.groups || { A: 0, B: 0 };
  setText('lhdr-pre-meta', `${pre.teams} equipos · Grupo A (${groups.A}) + Grupo B (${groups.B})`);
}

function findCurrentJornadaIdx(jornadas) {
  const now = Date.now();
  for (let i = 0; i < jornadas.length; i += 1) {
    const hasFuture = (jornadas[i].matches || []).some((m) => {
      if (!m.date) return false;
      const ts = Date.parse(m.date);
      return !Number.isNaN(ts) && ts >= now;
    });
    if (hasFuture) return i;
  }
  return jornadas.length - 1;
}

function renderLeague(kind) {
  const jornadas = getJornadas(kind);
  if (!jornadas.length) return;
  if (state.idx[kind] >= jornadas.length) state.idx[kind] = jornadas.length - 1;
  if (state.idx[kind] < 0) state.idx[kind] = 0;

  const sel = $(`${kind}-sel`);
  sel.innerHTML = jornadas.map((j, i) => `<option value="${i}">${esc(j.name)}</option>`).join('');
  sel.value = state.idx[kind];
  renderJornada(kind, state.idx[kind]);
  renderTeams(kind);
}

function renderJornada(kind, idx) {
  state.idx[kind] = idx;
  const jornadas = getJornadas(kind);
  const jornada = jornadas[idx];
  const matches = getMatches(kind, jornada);

  $(`${kind}-prev`).disabled = idx <= 0;
  $(`${kind}-next`).disabled = idx >= jornadas.length - 1;
  $(`${kind}-meta`).textContent = `${jornada?.name || '—'} · ${matches.length} partidos`;

  const target = $(`${kind}-matches`);
  if (!matches.length) {
    target.innerHTML = '<div class="no-data">No hay partidos disponibles para esta jornada.</div>';
    return;
  }
  target.innerHTML = matches.map((m) => renderMatchCard(kind, m)).join('');
}

function renderMatchCard(kind, m) {
  const home = teamName(kind, m.home);
  const away = teamName(kind, m.away);
  const played = isPlayed(m);
  const future = isFuture(m) && !played;
  const huracan = home === 'AD HURACAN' || away === 'AD HURACAN';

  const cls = ['mc'];
  if (played) cls.push('played');
  if (future) cls.push('nxt');
  if (huracan) cls.push('fav');
  if (m.status === 10 || m.home === -1 || m.away === -1) cls.push('bye');

  const score = played ? `${m.home_score} - ${m.away_score}` : 'vs';
  const badge = played
    ? '<span class="sb sb-played">Finalizado</span>'
    : future
      ? '<span class="sb sb-nxt">Próximo</span>'
      : `<span class="sb sb-pend">${esc(STATUS[m.status] || 'Pendiente')}</span>`;

  const avClass = (k, id) =>
    k === 'mini' ? 'm' : teamGroup(k, id) === 'A' ? 'pa' : 'pb';

  return `<article class="${cls.join(' ')}">
    <div class="mc-body">
      <div class="mc-side">
        ${avatarHTML(`mc-av ${avClass(kind, m.home)}`, home)}
        <div class="mc-tname">${esc(home)}</div>
      </div>
      <div class="mc-ctr">
        <div class="mc-day">${esc(fmtDate(m.date))}</div>
        <div class="mc-time">${esc(score)}</div>
        ${badge}
      </div>
      <div class="mc-side">
        ${avatarHTML(`mc-av ${avClass(kind, m.away)}`, away)}
        <div class="mc-tname">${esc(away)}</div>
      </div>
    </div>
    <div class="mc-field">${esc(m.field || 'Campo pendiente')}</div>
  </article>`;
}

function fmtDateHuman(v) {
  if (!v) return 'Sin fecha';
  try {
    const d = new Date(v);
    return d.toLocaleString('es-ES', {
      weekday: 'long', day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit',
    });
  } catch { return v; }
}

function renderHuracanCard(m) {
  const played = isPlayed(m);
  const future = isFuture(m) && !played;
  const bye = m.status === 10 || m.home === -1 || m.away === -1;

  const cls = ['mc', 'fav'];
  if (played) cls.push('played');
  if (future) cls.push('nxt');
  if (bye) cls.push('bye');

  const score = played ? `${m.home_score} - ${m.away_score}` : bye ? '—' : 'vs';
  const badge = bye
    ? '<span class="sb sb-pend">Descansa</span>'
    : played
      ? '<span class="sb sb-played">Finalizado</span>'
      : future
        ? '<span class="sb sb-nxt">Próximo</span>'
        : `<span class="sb sb-pend">${esc(STATUS[m.status] || 'Pendiente')}</span>`;

  return `<article class="${cls.join(' ')}">
    <div class="mc-body">
      <div class="mc-side">
        ${avatarHTML('mc-av m', m.home_name)}
        <div class="mc-tname">${esc(m.home_name)}</div>
      </div>
      <div class="mc-ctr">
        <div class="mc-day">${esc(fmtDate(m.date))}</div>
        <div class="mc-time">${esc(score)}</div>
        ${badge}
      </div>
      <div class="mc-side">
        ${avatarHTML('mc-av m', m.away_name)}
        <div class="mc-tname">${esc(m.away_name)}</div>
      </div>
    </div>
    <div class="mc-field">${esc(m.jornada || '')}${m.field ? ' · ' + esc(m.field) : ''}</div>
  </article>`;
}

function renderHuracan() {
  const all = state.data.huracan?.mini || [];
  if (!all.length) {
    $('hur-list').innerHTML = '<div class="hur-empty">No hay partidos todavía.</div>';
    return;
  }

  const now = Date.now();
  const next = [...all]
    .filter((m) => !(m.status === 10 || m.home === -1 || m.away === -1))
    .filter((m) => {
      if (!m.date) return false;
      const ts = Date.parse(m.date);
      return !Number.isNaN(ts) && ts >= now;
    })
    .sort((a, b) => a.date.localeCompare(b.date))[0];

  $('hur-next').innerHTML = next
    ? `<div class="hur-next-card">
         <div class="hnc-top">
           <div class="hnc-jornada">${esc(next.jornada || '—')}</div>
           <div class="hnc-when">${esc(fmtDateHuman(next.date))}</div>
         </div>
         <div class="hnc-teams">${esc(next.home_name)} <span class="vs">vs</span> ${esc(next.away_name)}</div>
         <div class="hnc-field">${esc(next.field || 'Campo por confirmar')}</div>
       </div>`
    : '<div class="hur-empty">No hay próximo partido programado.</div>';

  const jornNum = (m) =>
    parseInt((m.jornada || '').match(/\d+/)?.[0] || '0', 10);
  const nextJorn = next ? jornNum(next) : 0;
  const upcoming = [...all]
    .filter((m) => !(m.status === 10 || m.home === -1 || m.away === -1))
    .filter((m) => !isPlayed(m))
    .filter((m) => jornNum(m) > nextJorn)
    .sort((a, b) => jornNum(a) - jornNum(b));
  $('hur-current-title').textContent = 'Próximos partidos';
  $('hur-current').innerHTML = upcoming.length
    ? upcoming.map(renderHuracanCard).join('')
    : '<div class="hur-empty">No hay más partidos próximos.</div>';

  const chronological = [...all].sort((a, b) => jornNum(a) - jornNum(b));
  $('hur-list').innerHTML = chronological.map(renderHuracanCard).join('');

  const meta = state.data.meta;
  const real = all.filter((m) => !(m.home === -1 || m.away === -1)).length;
  if (meta) {
    $('lhdr-hur-meta').textContent = `${meta.season} · ${real} partidos en calendario`;
  }
}

function renderTeams(kind) {
  const teams = Object.entries(state.data[kind]?.teams || {})
    .map(([id, val]) => kind === 'mini'
      ? { id: +id, name: val, group: '-' }
      : { id: +id, name: val.name, group: val.group || 'A' })
    .filter((t) => kind !== 'pre' || t.group === state.preGroup)
    .sort((a, b) => a.name.localeCompare(b.name));

  $(`${kind}-teams`).innerHTML = teams.map((t) =>
    `<div class="tcrd">
       ${avatarHTML(`tav ${kind === 'mini' ? 'm' : t.group === 'A' ? 'pa' : 'pb'}`, t.name)}
       <div>
         <div class="tname">${esc(t.name)}</div>
         ${kind === 'pre' ? `<span class="tgrp ${t.group === 'A' ? 'ga' : 'gb'}">Grupo ${t.group}</span>` : ''}
       </div>
     </div>`).join('');
}

function showLeague(kind) {
  state.league = kind;
  $('sec-mini').classList.toggle('on', kind === 'mini');
  $('sec-pre').classList.toggle('on', kind === 'pre');
  $('sec-huracan').classList.toggle('on', kind === 'huracan');
  document.querySelectorAll('.npill').forEach((el) => el.classList.remove('on'));
  const pillKey = kind === 'huracan' ? 'hur' : kind;
  document.querySelector(`.npill.${pillKey}`)?.classList.add('on');
}

function switchTab(kind, tab, btn) {
  state.tab[kind] = tab;
  document.querySelectorAll(`#sec-${kind} .itab`).forEach((el) => el.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll(`#sec-${kind} .panel`).forEach((el) => el.classList.remove('on'));
  $(`${kind}-${tab}`).classList.add('on');
}

function switchGrp(group) {
  state.preGroup = group;
  $('gA').classList.toggle('on-a', group === 'A');
  $('gB').classList.toggle('on-b', group === 'B');
  state.idx.pre = findCurrentJornadaIdx(getJornadas('pre'));
  renderLeague('pre');
}

function chJorn(kind, delta) {
  renderJornada(kind, state.idx[kind] + delta);
  $(`${kind}-sel`).value = state.idx[kind];
}

function toggleFull() {
  const list = $('hur-list');
  const current = $('hur-current');
  const title = $('hur-current-title');
  const label = $('hur-full-toggle-label');
  const showingFull = list.classList.toggle('hur-full-hidden') === false;
  current.classList.toggle('hur-full-hidden', showingFull);
  title.textContent = showingFull ? 'Calendario completo' : 'Próximos partidos';
  label.textContent = showingFull ? 'Ver próximos partidos' : 'Ver calendario completo';
}

async function loadData() {
  const bust = Date.now();
  const load = (name) =>
    fetch(`./data/${name}?v=${bust}`, { cache: 'no-store' }).then((r) => r.json());
  const [mini, pre, huracan, meta] = await Promise.all([
    load('mini.json'),
    load('pre.json'),
    load('huracan.json'),
    load('meta.json'),
  ]);
  state.data = { mini, pre, huracan, meta };
}

async function init() {
  await loadData();
  renderHeaders();
  state.idx.mini = findCurrentJornadaIdx(getJornadas('mini'));
  state.idx.pre = findCurrentJornadaIdx(getJornadas('pre'));
  renderLeague('mini');
  renderLeague('pre');
  renderHuracan();
  showLeague('huracan');
}

window.showLeague = showLeague;
window.switchTab = switchTab;
window.switchGrp = switchGrp;
window.chJorn = chJorn;
window.renderJornada = renderJornada;
window.toggleFull = toggleFull;

init().catch((err) => {
  console.error(err);
  document.body.innerHTML =
    '<div class="no-data" style="margin-top:120px">Error cargando la web. Revisa los JSON generados.</div>';
});
