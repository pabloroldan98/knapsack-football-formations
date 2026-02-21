/* ═══════════════════════════════════════════════════════════════════════════
   Calculadora Fantasy – Main Application JavaScript
   ═══════════════════════════════════════════════════════════════════════════ */

// ─── Configuration ──────────────────────────────────────────────────────────
// Change this to your deployed API URL in production
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'https://knapsack-football-formations.onrender.com'; // <-- CHANGE this to your backend URL

// ─── i18n ───────────────────────────────────────────────────────────────────
const I18N = {
  es: {
    "app.title": "Calculadora Fantasy",
    "sb.options": "Opciones", "sb.lang": "Idioma",
    "sb.competition": "Competición", "sb.app": "Aplicación",
    "sb.penalties": "¿Te importan los penaltis?",
    "sb.sort_by": "Ordenar por",
    "sb.use_start_prob_with_value": "Utilizar '% Titular' con Rentabilidad",
    "sb.jornada": "Jornada", "sb.num_jornadas": "Jornadas a considerar",
    "sb.ignore_form": "¿Ignorar estado de forma?",
    "sb.ignore_fixtures": "¿Ignorar dificultad del partido?",
    "btn.load_players": "Cargar Jugadores",
    "opt.yes": "Sí", "opt.no": "No",
    "sort.score": "Puntuación", "sort.worth": "Rentabilidad", "sort.price": "Precio",
    "sort.form": "Forma", "sort.fixture": "Partido",
    "sort.startprobability": "Probabilidad", "sort.position": "Posición",
    "num.one": "Una jornada", "num.two": "Dos jornadas", "num.three": "Tres jornadas",
    "tab.best11_budget": "💰 Mejores 11s con presupuesto",
    "tab.my_best11": "⚽ Mi mejor 11 posible",
    "tab.players_list": "📋 Lista de jugadores",
    "tab.my_market": "📈 Analizar mi mercado",
    "h.budget11": "Mejores 11s dentro de tu presupuesto",
    "h.my_best11": "Selecciona Jugadores para tu 11 ideal",
    "h.players_list": "Lista de Jugadores Actualizada",
    "h.market": "Selecciona los Jugadores de tu mercado",
    "blind.header": "Blindar o Excluir jugadores",
    "blind.title": "🔒 Jugadores blindados",
    "blind.caption1": "Estos jugadores estarán sí o sí en todos los equipos calculados",
    "blind.add": "Añadir blindado",
    "ban.title": "🚫 Jugadores excluidos",
    "ban.caption": "Estos jugadores no estarán en ningún equipo calculado",
    "ban.add": "Añadir excluido",
    "sb.budget.max": "Presupuesto máximo disponible",
    "sb.budget.hint": "Pon -1 si quieres presupuesto ilimitado",
    "sb.extra_filters": "Filtros adicionales",
    "sb.exclude_hard_fixtures": "Excluir jugadores con partidos difíciles",
    "sb.start_prob_range": "Probabilidad de ser titular (%)",
    "sb.premium_formations": "Formaciones Premium",
    "btn.calc11": "Calcular 11s",
    "btn.ready": "Listo",
    "btn.add": "Añadir",
    "cap.add_all": "Añade a todos los jugadores de tu equipo para calcular tu 11 ideal",
    "cap.market": "Selecciona los Jugadores que han salido en tu mercado para compararlos",
    "filters.more": "Filtros adicionales",
    "filters.complete_more": "Filtros adicionales sobre tu lista",
    "filters.fixture": "Filtrar por dificultad de partido",
    "filters.price": "Filtrar por precio (M)",
    "filters.position": "Filtrar por posición:",
    "filters.teams": "Filtrar por equipos",
    "pos.gk": "Portero", "pos.def": "Defensa", "pos.mid": "Mediocentro", "pos.att": "Delantero",
    "players.legend": "· <b>Jugador</b> (Posición, Equipo): Precio - <b>Puntuación</b><br><i>(Forma, Partido, Titular %)</i>",
    "players.found": "jugadores encontrados",
    "btn.copy_players": "📋 Copiar jugadores",
    "btn.copy_players_full": "📋 Copiar (datos completos)",
    "footer.contact": "Contacto",
    "footer.privacy": "Política de Privacidad",
    "footer.cookies": "Preferencias de cookies",
    "player.form": "Forma", "player.fixture": "Partido", "player.titular": "Titular",
    "formations.name": "Formación", "formations.points": "puntos",
    "formations.see_all": "Ver todos los jugadores utilizados",
    "formations.premotivo": "No se pudo incluir a:",
    "formations.motivo2": " con el presupuesto dado",
    "loading.players": "Cargando jugadores...",
    "loading.calculating": "Calculando mejores combinaciones...",
    "warn.need_11": "Selecciona al menos 11 jugadores antes de continuar.",
    "warn.load_first": "Primero carga los jugadores con el botón del menú lateral.",
    "warn.not_enough": "No hay suficientes jugadores con los filtros actuales.",
    "toast.copied": "Copiado al portapapeles",
    "toast.loaded": "jugadores cargados",
    "blind.locked": "🔒 Blindado", "blind.lock": "Blindar",
    "cookie.text": "Este sitio usa cookies para mejorar tu experiencia y mostrar anuncios relevantes.",
    "cookie.privacy": "Política de Privacidad",
    "cookie.accept": "Aceptar", "cookie.reject": "Rechazar",
    "privacy.title": "Política de Privacidad",
    "privacy.p1": "En Calculadora Fantasy respetamos tu privacidad y nos comprometemos a proteger tus datos personales. Este sitio web no recopila datos personales sin tu consentimiento y no comparte información con terceros salvo obligación legal.",
    "privacy.p2": "Utilizamos Google Analytics para análisis de tráfico y Google AdSense para publicidad. Estos servicios pueden usar cookies. Puedes gestionar tus preferencias de cookies en cualquier momento.",
    "privacy.p3": "Podemos almacenar datos de uso anónimos (preferencias de configuración, competiciones consultadas) para mejorar el servicio. Estos datos no están vinculados a información personal identificable.",
    "privacy.p4": "Para más información o ejercer tus derechos de acceso, rectificación o supresión, escríbenos a",
    "privacy.close": "Cerrar",
    "cap.lock_note": "Nota: 'Blindar' jugadores obliga a que estén sí o sí en todos los equipos calculados",
    "cap.same_as_list": "Nota: es lo mismo que la 'Lista de jugadores', pero solo para los jugadores que selecciones",
    "squad.title": "Plantillas guardadas",
    "squad.save": "Guardar plantilla",
    "squad.name_placeholder": "Nombre de la plantilla",
    "squad.empty": "No hay plantillas guardadas",
    "squad.load": "Cargar",
    "squad.delete": "Borrar",
    "squad.saved_ok": "Plantilla guardada",
    "squad.deleted_ok": "Plantilla borrada",
    "squad.loaded_ok": "Plantilla cargada",
    "squad.players_count": "jugadores",
  },
  en: {
    "app.title": "Fantasy Calculator",
    "sb.options": "Options", "sb.lang": "Language",
    "sb.competition": "Competition", "sb.app": "App",
    "sb.penalties": "Do penalties matter?",
    "sb.sort_by": "Sort by",
    "sb.use_start_prob_with_value": "Use 'Start %' when sorting by Worth",
    "sb.jornada": "Matchweek", "sb.num_jornadas": "Matchweeks to consider",
    "sb.ignore_form": "Ignore form?",
    "sb.ignore_fixtures": "Ignore fixture difficulty?",
    "btn.load_players": "Load Players",
    "opt.yes": "Yes", "opt.no": "No",
    "sort.score": "Score", "sort.worth": "Worth", "sort.price": "Price",
    "sort.form": "Form", "sort.fixture": "Fixture",
    "sort.startprobability": "Start probability", "sort.position": "Position",
    "num.one": "One matchweek", "num.two": "Two matchweeks", "num.three": "Three matchweeks",
    "tab.best11_budget": "💰 Best lineups by budget",
    "tab.my_best11": "⚽ My best possible lineup",
    "tab.players_list": "📋 Players list",
    "tab.my_market": "📈 Analyze my market",
    "h.budget11": "Best lineups within your budget",
    "h.my_best11": "Select players for your ideal lineup",
    "h.players_list": "Updated Players List",
    "h.market": "Pick the players from your market",
    "blind.header": "Lock or Exclude players",
    "blind.title": "🔒 Locked players",
    "blind.caption1": "These players will always be in every calculated team",
    "blind.add": "Add locked",
    "ban.title": "🚫 Excluded players",
    "ban.caption": "These players will never be in any calculated team",
    "ban.add": "Add excluded",
    "sb.budget.max": "Maximum available budget",
    "sb.budget.hint": "Use -1 for unlimited budget",
    "sb.extra_filters": "Additional filters",
    "sb.exclude_hard_fixtures": "Exclude players with hard fixtures",
    "sb.start_prob_range": "Start probability (%)",
    "sb.premium_formations": "Premium formations",
    "btn.calc11": "Calculate lineups",
    "btn.ready": "Done",
    "btn.add": "Add",
    "cap.add_all": "Add all your squad to compute your best possible lineup",
    "cap.market": "Select players from your market to compare them",
    "filters.more": "More filters",
    "filters.complete_more": "Additional filters on your list",
    "filters.fixture": "Filter by fixture difficulty",
    "filters.price": "Filter by price (M)",
    "filters.position": "Filter by position:",
    "filters.teams": "Filter by teams",
    "pos.gk": "Goalkeeper", "pos.def": "Defender", "pos.mid": "Midfielder", "pos.att": "Forward",
    "players.legend": "· <b>Player</b> (Position, Team): Price - <b>Score</b><br><i>(Form, Fixture, Start %)</i>",
    "players.found": "players found",
    "btn.copy_players": "📋 Copy players",
    "btn.copy_players_full": "📋 Copy players (full data)",
    "footer.contact": "Contact",
    "footer.privacy": "Privacy Policy",
    "footer.cookies": "Cookie preferences",
    "player.form": "Form", "player.fixture": "Fixture", "player.titular": "Start",
    "formations.name": "Formation", "formations.points": "points",
    "formations.see_all": "See all players used",
    "formations.premotivo": "Could not include:",
    "formations.motivo2": " with the given budget",
    "loading.players": "Loading players...",
    "loading.calculating": "Calculating best combinations...",
    "warn.need_11": "Select at least 11 players before continuing.",
    "warn.load_first": "Load players first using the sidebar button.",
    "warn.not_enough": "Not enough players with current filters.",
    "toast.copied": "Copied to clipboard",
    "toast.loaded": "players loaded",
    "blind.locked": "🔒 Locked", "blind.lock": "Lock",
    "cookie.text": "This site uses cookies to improve your experience and show relevant ads.",
    "cookie.privacy": "Privacy Policy",
    "cookie.accept": "Accept", "cookie.reject": "Reject",
    "privacy.title": "Privacy Policy",
    "privacy.p1": "At Calculadora Fantasy we respect your privacy and are committed to protecting your personal data. This website does not collect personal data without your consent and does not share information with third parties except as required by law.",
    "privacy.p2": "We use Google Analytics for traffic analysis and Google AdSense for advertising. These services may use cookies. You can manage your cookie preferences at any time.",
    "privacy.p3": "We may store anonymous usage data (configuration preferences, competitions viewed) to improve the service. This data is not linked to personally identifiable information.",
    "privacy.p4": "For more information or to exercise your rights of access, rectification, or deletion, write to us at",
    "privacy.close": "Close",
    "cap.lock_note": "Note: 'Locking' players forces them into all calculated teams",
    "cap.same_as_list": "Note: same as the 'Players list' but only for the players you select",
    "squad.title": "Saved squads",
    "squad.save": "Save squad",
    "squad.name_placeholder": "Squad name",
    "squad.empty": "No saved squads",
    "squad.load": "Load",
    "squad.delete": "Delete",
    "squad.saved_ok": "Squad saved",
    "squad.deleted_ok": "Squad deleted",
    "squad.loaded_ok": "Squad loaded",
    "squad.players_count": "players",
  }
};

// ─── Session ID (persists per browser tab) ──────────────────────────────────
const SESSION_ID = sessionStorage.getItem('sid') || (() => {
  const id = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36);
  sessionStorage.setItem('sid', id);
  return id;
})();

// ─── State ──────────────────────────────────────────────────────────────────
let LANG = 'es';
let allPlayers = [];        // Full player list from API
let divideMillions = false;
let isLaLiga = true;
let isTournament = false;
let teamsList = [];

// Tab-specific state
const blindedNames = new Set();
const bannedNames = new Set();
const my11Names = new Set();
const my11Locked = new Set();
const marketNames = new Set();
const selectedTeamsFilter = new Set();

// ─── LocalStorage persistence ───────────────────────────────────────────────
const LS_STATE_KEY = 'cf_app_state';

function persistState() {
  try {
    const state = {
      blinded: [...blindedNames],
      banned: [...bannedNames],
      my11: [...my11Names],
      my11Locked: [...my11Locked],
      market: [...marketNames],
      teamsFilter: [...selectedTeamsFilter],
      filters: _collectFilters(),
    };
    localStorage.setItem(LS_STATE_KEY, JSON.stringify(state));
  } catch (_) {}
}

function _collectFilters() {
  const val = id => document.getElementById(id)?.value ?? null;
  const chk = id => document.getElementById(id)?.checked ?? null;
  return {
    selCompetition: val('selCompetition'),
    selApp: val('selApp'),
    selPenalties: val('selPenalties'),
    selSort: val('selSort'),
    selWorthProb: val('selWorthProb'),
    selJornada: val('selJornada'),
    selNumJornadas: val('selNumJornadas'),
    selIgnoreForm: val('selIgnoreForm'),
    selIgnoreFixtures: val('selIgnoreFixtures'),
    budgetInput: val('budgetInput'),
    budgetFixtureFilter: val('budgetFixtureFilter'),
    budgetMinProb: val('budgetMinProb'),
    budgetPremium: chk('budgetPremium'),
    my11FixtureFilter: val('my11FixtureFilter'),
    my11MinProb: val('my11MinProb'),
    my11Premium: chk('my11Premium'),
    playersFixtureFilter: val('playersFixtureFilter'),
    playersMinProb: val('playersMinProb'),
    filterGK: chk('filterGK'),
    filterDEF: chk('filterDEF'),
    filterMID: chk('filterMID'),
    filterATT: chk('filterATT'),
    marketFixtureFilter: val('marketFixtureFilter'),
    marketMinProb: val('marketMinProb'),
  };
}

function restoreState() {
  try {
    const raw = localStorage.getItem(LS_STATE_KEY);
    if (!raw) return;
    const state = JSON.parse(raw);

    if (state.blinded) state.blinded.forEach(n => blindedNames.add(n));
    if (state.banned) state.banned.forEach(n => bannedNames.add(n));
    if (state.my11) state.my11.forEach(n => my11Names.add(n));
    if (state.my11Locked) state.my11Locked.forEach(n => my11Locked.add(n));
    if (state.market) state.market.forEach(n => marketNames.add(n));
    if (state.teamsFilter) state.teamsFilter.forEach(n => selectedTeamsFilter.add(n));

    if (state.filters) _applyFilters(state.filters);
  } catch (_) {}
}

function _applyFilters(f) {
  const setVal = (id, v) => { const el = document.getElementById(id); if (el && v !== null && v !== undefined) el.value = v; };
  const setChk = (id, v) => { const el = document.getElementById(id); if (el && v !== null && v !== undefined) el.checked = v; };

  setVal('selCompetition', f.selCompetition);
  setVal('selApp', f.selApp);
  setVal('selPenalties', f.selPenalties);
  setVal('selSort', f.selSort);
  setVal('selWorthProb', f.selWorthProb);
  setVal('selJornada', f.selJornada);
  setVal('selNumJornadas', f.selNumJornadas);
  setVal('selIgnoreForm', f.selIgnoreForm);
  setVal('selIgnoreFixtures', f.selIgnoreFixtures);
  setVal('budgetInput', f.budgetInput);
  setVal('budgetFixtureFilter', f.budgetFixtureFilter);
  setVal('budgetMinProb', f.budgetMinProb);
  setChk('budgetPremium', f.budgetPremium);
  setVal('my11FixtureFilter', f.my11FixtureFilter);
  setVal('my11MinProb', f.my11MinProb);
  setChk('my11Premium', f.my11Premium);
  setVal('playersFixtureFilter', f.playersFixtureFilter);
  setVal('playersMinProb', f.playersMinProb);
  setChk('filterGK', f.filterGK);
  setChk('filterDEF', f.filterDEF);
  setChk('filterMID', f.filterMID);
  setChk('filterATT', f.filterATT);
  setVal('marketFixtureFilter', f.marketFixtureFilter);
  setVal('marketMinProb', f.marketMinProb);

  // Update range labels
  const bmpEl = document.getElementById('budgetMinProbVal');
  if (bmpEl && f.budgetMinProb !== null) bmpEl.textContent = f.budgetMinProb + '%';
  const m11pEl = document.getElementById('my11MinProbVal');
  if (m11pEl && f.my11MinProb !== null) m11pEl.textContent = f.my11MinProb + '%';
  const ppEl = document.getElementById('playersMinProbVal');
  if (ppEl && f.playersMinProb !== null) ppEl.textContent = f.playersMinProb + '%';
  const mmpEl = document.getElementById('marketMinProbVal');
  if (mmpEl && f.marketMinProb !== null) mmpEl.textContent = f.marketMinProb + '%';

  // Worth prob container visibility
  const isWorth = f.selSort === 'worth';
  const wpc = document.getElementById('worthProbContainer');
  if (wpc) wpc.style.display = isWorth ? 'block' : 'none';

  // Re-apply range visual fills
  for (const id of ['budgetMinProb', 'my11MinProb', 'playersMinProb', 'marketMinProb']) {
    const el = document.getElementById(id);
    if (el) updateRangeRightFill(el);
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function t(key) { return (I18N[LANG] || I18N.es)[key] || key; }

function showLoading(text, withProgress = false) {
  const el = document.getElementById('loadingOverlay');
  document.getElementById('loadingText').textContent = text || t('loading.players');
  const progContainer = document.getElementById('progressContainer');
  const progBar = document.getElementById('progressBar');
  const progPct = document.getElementById('progressPct');

  if (withProgress) {
    progContainer.style.display = 'flex';
    progBar.style.width = '0%';
    progPct.textContent = '0%';
  } else {
    progContainer.style.display = 'none';
  }
  el.classList.add('visible');
}

function hideLoading() {
  setProgress(100);
  setTimeout(() => {
    document.getElementById('loadingOverlay').classList.remove('visible');
    document.getElementById('progressContainer').style.display = 'none';
  }, 350);
}

function setProgress(pct) {
  const bar = document.getElementById('progressBar');
  const label = document.getElementById('progressPct');
  if (bar) bar.style.width = Math.round(pct) + '%';
  if (label) label.textContent = Math.round(pct) + '%';
}

async function apiPostSSE(path, body) {
  const resp = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.type === 'progress') {
        setProgress(payload.percent);
      } else if (payload.type === 'result') {
        result = payload.data;
      }
    }
  }

  if (buffer.startsWith('data: ')) {
    const payload = JSON.parse(buffer.slice(6));
    if (payload.type === 'result') result = payload.data;
  }

  return result;
}

function showToast(msg) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 2000);
}

function getArrowStyle(val, minVal = 0.96, maxVal = 1.05) {
  let angle;
  if (val >= maxVal) angle = 90;
  else if (val <= minVal) angle = -90;
  else if (val >= 1) angle = ((val - 1) / (maxVal - 1)) * 90;
  else angle = ((val - 1) / (1 - minVal)) * 90;

  let r, g;
  if (val >= maxVal) { r = 0; g = 255; }
  else if (val <= minVal) { r = 255; g = 0; }
  else if (val >= 1) {
    const ratio = (val - 1) / (maxVal - 1);
    r = Math.round(255 * (1 - ratio));
    g = 255;
  } else {
    const ratio = (val - minVal) / (1 - minVal);
    r = 255;
    g = Math.round(255 * ratio);
  }

  return { rotation: -angle, color: `rgb(${r},${g},0)` };
}

function renderArrow(val) {
  const { rotation, color } = getArrowStyle(val);
  return `<span class="arrow-indicator" style="color:${color};transform:rotate(${rotation}deg);display:inline-block">→</span>`;
}

function normalize(str) {
  return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

// ─── Sorting ────────────────────────────────────────────────────────────────
function percentileRanksDict(arr) {
  const sorted = [...new Set(arr)].sort((a, b) => a - b);
  const n = arr.length;
  const result = {};
  for (const x of sorted) {
    result[x] = arr.filter(v => v <= x).length / n;
  }
  return result;
}

function sortPlayers(players, sortBy, useStartProb = true) {
  const arr = [...players];
  if (sortBy === 'worth') {
    const values = arr.map(p => p.value);
    const prices = arr.map(p => p.raw_price || p.price);
    const vRanks = percentileRanksDict(values);
    const pRanks = percentileRanksDict(prices);
    const minPrice = Math.min(...prices.filter(p => p > 0)) || 1;
    const minPriceP = pRanks[0] !== undefined ? pRanks[0] : (prices.filter(v => v <= minPrice).length / prices.length);
    arr.sort((a, b) => {
      const aVR = vRanks[a.value] || 0;
      const bVR = vRanks[b.value] || 0;
      const aPR = Math.max(pRanks[a.raw_price || a.price] || 0, minPriceP);
      const bPR = Math.max(pRanks[b.raw_price || b.price] || 0, minPriceP);
      if (useStartProb) {
        const aW = (aVR * a.start_probability) / aPR;
        const bW = (bVR * b.start_probability) / bPR;
        return bW - aW || bVR / aPR - aVR / bPR || b.value - a.value;
      }
      return (bVR / bPR) - (aVR / aPR) || b.value - a.value;
    });
  } else if (sortBy === 'price') {
    arr.sort((a, b) => b.price - a.price || b.value - a.value);
  } else if (sortBy === 'form') {
    arr.sort((a, b) => b.form - a.form || b.value - a.value);
  } else if (sortBy === 'fixture') {
    arr.sort((a, b) => b.fixture - a.fixture || b.value - a.value);
  } else if (sortBy === 'startprobability') {
    arr.sort((a, b) => b.start_probability - a.start_probability || b.value - a.value);
  } else if (sortBy === 'position') {
    const pri = { GK: 0, DEF: 1, MID: 2, ATT: 3 };
    arr.sort((a, b) => (pri[a.position] || 9) - (pri[b.position] || 9) || b.value - a.value);
  } else {
    arr.sort((a, b) => b.value - a.value || b.form - a.form || b.fixture - a.fixture);
  }
  return arr;
}

// ─── API Client ─────────────────────────────────────────────────────────────
async function apiGet(path, params = {}) {
  const url = new URL(API_BASE + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== '' && v !== undefined && v !== null) url.searchParams.set(k, v);
  }
  const resp = await fetch(url.toString());
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

async function apiPost(path, body) {
  const resp = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json();
}

// ─── Rendering: Player Card ────────────────────────────────────────────────
function renderPlayerCard(p, options = {}) {
  const { showRemove = false, removeCallback = null, showLock = false, lockCallback = null, isLocked = false } = options;
  const unit = 'M';
  const card = document.createElement('div');
  card.className = 'player-card';

  const imgEl = p.img_link ? `<img src="${p.img_link}" class="player-img" alt="" loading="lazy" onerror="this.src='https://cdn.biwenger.com/i/p/0.png'">` : '';

  let actionsHtml = '';
  if (showLock) {
    const lockLabel = isLocked ? t('blind.locked') : t('blind.lock');
    const lockClass = isLocked ? 'btn-lock locked' : 'btn-lock';
    actionsHtml += `<button class="${lockClass}" data-name="${p.name}">${lockLabel}</button>`;
  }
  if (showRemove) {
    actionsHtml += `<button class="btn-remove" data-name="${p.name}">❌</button>`;
  }

  card.innerHTML = `
    ${imgEl}
    <div class="player-info">
      <div class="player-name">${p.name}</div>
      <div class="player-details">${p.position} · ${p.team} · ${p.price}${unit} · <b>${p.show_value} pts</b></div>
    </div>
    <div class="player-stats">
      <div class="stat">
        <div class="stat-arrow">${renderArrow(p.form)}</div>
        <div>${t('player.form')}</div>
      </div>
      <div class="stat">
        <div class="stat-arrow">${renderArrow(p.fixture)}</div>
        <div>${t('player.fixture')}</div>
      </div>
      <div class="stat">
        <div class="stat-value">${(p.start_probability * 100).toFixed(0)}%</div>
        <div>${t('player.titular')}</div>
      </div>
    </div>
    <div class="player-actions">${actionsHtml}</div>
  `;

  if (showRemove) {
    card.querySelector('.btn-remove').addEventListener('click', () => removeCallback && removeCallback(p.name));
  }
  if (showLock) {
    card.querySelector('.btn-lock').addEventListener('click', () => lockCallback && lockCallback(p.name));
  }

  return card;
}

// ─── Rendering: Formation Result ────────────────────────────────────────────
function renderFormationResult(fr) {
  const div = document.createElement('div');
  div.className = 'formation-result';

  let headerTxt = `${t('formations.name')} [${fr.formation.join('-')}]: ${fr.score} ${t('formations.points')} – 💰 ${fr.total_price}M`;
  let warningsHtml = '';
  if (fr.missing_blinded && fr.missing_blinded.length > 0) {
    for (const name of fr.missing_blinded) {
      warningsHtml += `<div class="formation-warning">⚠️ ${t('formations.premotivo')} <b>${name}</b>${t('formations.motivo2')}</div>`;
    }
  }

  let linesHtml = '';
  for (const pos of ['ATT', 'MID', 'DEF', 'GK']) {
    const line = fr.lines[pos] || [];
    if (line.length === 0) continue;
    linesHtml += '<div class="formation-line">';
    for (const pl of line) {
      const blindedClass = pl.is_blinded ? ' blinded' : '';
      const lockIcon = pl.is_blinded ? '🔒 ' : '';
      linesHtml += `
        <div class="formation-player${blindedClass}">
          <img src="${pl.img_link}" alt="" loading="lazy" onerror="this.src='https://cdn.biwenger.com/i/p/0.png'">
          <div class="fp-name">${lockIcon}${pl.name}</div>
          <div class="fp-prob">${(pl.start_probability * 100).toFixed(0)}%</div>
        </div>`;
    }
    linesHtml += '</div>';
  }

  // Expandable full player list
  let expandHtml = `<details class="expander" style="margin-top:8px"><summary>${t('formations.see_all')}</summary><div class="expander-content players-list">`;
  for (const pl of fr.players) {
    const lockIcon = pl.is_blinded ? '🔒 ' : '';
    expandHtml += `<div class="player-card" style="padding:6px 8px">
      <div class="player-info"><span class="player-name">${lockIcon}${pl.name}</span>
      <span class="player-details">${pl.position} · ${pl.team} · ${pl.price}M · <b>${pl.show_value} pts</b></span></div>
      <div class="player-stats">
        <div class="stat">${renderArrow(pl.form)}<div>${t('player.form')}</div></div>
        <div class="stat">${renderArrow(pl.fixture)}<div>${t('player.fixture')}</div></div>
        <div class="stat"><div class="stat-value">${(pl.start_probability * 100).toFixed(0)}%</div><div>${t('player.titular')}</div></div>
      </div>
    </div>`;
  }
  expandHtml += '</div></details>';

  div.innerHTML = `
    <div class="formation-header">${headerTxt}</div>
    ${warningsHtml}
    ${linesHtml}
    ${expandHtml}
  `;
  return div;
}

// ─── Datalist updater ───────────────────────────────────────────────────────
function updateDatalist(datalistId, players, excludeNames = new Set()) {
  const dl = document.getElementById(datalistId);
  dl.innerHTML = '';
  for (const p of players) {
    if (excludeNames.has(p.name)) continue;
    const opt = document.createElement('option');
    opt.value = p.name;
    opt.textContent = `${p.name} (${p.position}, ${p.team})`;
    dl.appendChild(opt);
  }
}

// ─── i18n: Apply translations to DOM ────────────────────────────────────────
function applyI18N() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    const txt = t(key);
    if (el.tagName === 'INPUT' && el.type !== 'checkbox') {
      el.placeholder = txt;
    } else {
      if (txt.includes('<')) el.innerHTML = txt;
      else el.textContent = txt;
    }
  });
  // Options
  document.querySelectorAll('[data-i18n-opt]').forEach(el => {
    el.textContent = t(el.dataset.i18nOpt);
  });
  document.documentElement.lang = LANG;
  document.getElementById('btnLangES').classList.toggle('active', LANG === 'es');
  document.getElementById('btnLangEN').classList.toggle('active', LANG === 'en');

  // Update URL
  const url = new URL(window.location.href);
  url.searchParams.set('lang', LANG);
  history.replaceState(null, '', url.toString());
}

// ─── Language ───────────────────────────────────────────────────────────────
function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem('lang', lang); } catch (_) {}
  applyI18N();
  // Re-render visible content
  renderPlayersTab();
  renderMarketTab();
  renderSquadList();
}

function initLang() {
  const params = new URLSearchParams(window.location.search);
  const qLang = params.get('lang');
  if (qLang === 'es' || qLang === 'en') { LANG = qLang; }
  else {
    try { const saved = localStorage.getItem('lang'); if (saved) LANG = saved; } catch (_) {}
    if (!LANG || (LANG !== 'es' && LANG !== 'en')) {
      LANG = navigator.language?.startsWith('en') ? 'en' : 'es';
    }
  }
}

// ─── Sidebar: Competitions ──────────────────────────────────────────────────
async function loadCompetitions() {
  try {
    const data = await apiGet('/api/competitions');
    const sel = document.getElementById('selCompetition');
    sel.innerHTML = '';
    for (const c of data.competitions) {
      const opt = document.createElement('option');
      opt.value = c.key;
      opt.textContent = LANG === 'en' ? c.name_en : c.name_es;
      sel.appendChild(opt);
    }
    sel.addEventListener('change', onCompetitionChange);
    // Restore persisted state (filters + player Sets) before first load
    restoreState();
    onCompetitionChange();
    loadPlayers();
  } catch (e) {
    console.error('Error loading competitions:', e);
  }
}

function onCompetitionChange() {
  const comp = document.getElementById('selCompetition').value;
  isLaLiga = (comp === 'laliga');
  isTournament = ['mundialito', 'champions', 'europaleague', 'conference'].includes(comp);

  // Show/hide jornada
  document.getElementById('jornadaContainer').style.display = isLaLiga ? 'block' : 'none';

  // Update app options
  const selApp = document.getElementById('selApp');
  if (isLaLiga) {
    selApp.innerHTML = '<option value="biwenger">Biwenger</option><option value="laligafantasy">LaLiga Fantasy</option>';
  } else {
    selApp.innerHTML = '<option value="biwenger">Biwenger</option>';
  }

  // Load jornadas if LaLiga
  if (isLaLiga) loadJornadas(comp);

  // Update budget input step
  updateBudgetInput();
}

async function loadJornadas(competition) {
  try {
    const data = await apiGet('/api/jornadas', { competition });
    const sel = document.getElementById('selJornada');
    sel.innerHTML = `<option value="">${LANG === 'en' ? 'Next match' : 'Siguiente partido'}</option>`;
    for (const j of data.jornadas) {
      const opt = document.createElement('option');
      opt.value = j.key;
      opt.textContent = j.label.replace('Jornada', t('sb.jornada'));
      sel.appendChild(opt);
    }
  } catch (e) {
    console.error('Error loading jornadas:', e);
  }
}

function updateBudgetInput() {
  const isBiwenger = document.getElementById('selApp').value === 'biwenger';
  const budgetInput = document.getElementById('budgetInput');
  if (!isTournament && isBiwenger) {
    budgetInput.step = '0.1';
    budgetInput.value = '30.0';
  } else {
    budgetInput.step = '1';
    budgetInput.value = '200';
  }
}

// ─── Load Players ───────────────────────────────────────────────────────────
let _isLoadingPlayers = false;
let _hasLoadedOnce = false;
async function loadPlayers() {
  if (_isLoadingPlayers) return;
  _isLoadingPlayers = true;
  const comp = document.getElementById('selCompetition').value;
  const app = document.getElementById('selApp').value;
  const ignoreForm = document.getElementById('selIgnoreForm').value === 'yes';
  const ignoreFixtures = document.getElementById('selIgnoreFixtures').value === 'yes';
  const ignorePenalties = document.getElementById('selPenalties').value === 'no';
  const jornadaKey = document.getElementById('selJornada')?.value || '';
  const numJornadas = parseInt(document.getElementById('selNumJornadas')?.value || '1');

  showLoading(t('loading.players'));
  try {
    const data = await apiGet('/api/players', {
      competition: comp, app, ignore_form: ignoreForm,
      ignore_fixtures: ignoreFixtures, ignore_penalties: ignorePenalties,
      jornada_key: jornadaKey, num_jornadas: numJornadas,
      session_id: SESSION_ID,
    });

    allPlayers = data.players;
    divideMillions = data.divide_millions;
    isLaLiga = data.is_laliga;
    isTournament = data.is_tournament;
    teamsList = data.teams;

    // Only clear teams on reloads, not the initial load with restored state
    if (_hasLoadedOnce) selectedTeamsFilter.clear();
    _hasLoadedOnce = true;
    updateTeamsDatalist();
    renderTeamChips();

    // Update all datalists
    updateAllDatalists();

    // Render all tabs that depend on player data (includes restored Sets)
    renderBlindedList();
    renderBannedList();
    renderPlayersTab();
    renderMy11List();
    renderMarketTab();

    // Update price slider range
    const maxPlayerPrice = Math.max(...allPlayers.map(p => p.price), 1);
    updatePriceSliderRange(maxPlayerPrice);

    hideLoading();
    showToast(`${allPlayers.length} ${t('toast.loaded')}`);

    // Close sidebar on mobile
    document.getElementById('sidebar').classList.remove('open');
    document.querySelector('.sidebar-backdrop')?.classList.remove('visible');

  } catch (e) {
    hideLoading();
    console.error('Error loading players:', e);
  } finally {
    _isLoadingPlayers = false;
  }
}

function updateAllDatalists() {
  updateDatalist('blindedDatalist', allPlayers, new Set([...blindedNames, ...bannedNames]));
  updateDatalist('bannedDatalist', allPlayers, new Set([...blindedNames, ...bannedNames]));
  updateDatalist('my11Datalist', allPlayers, my11Names);
  updateDatalist('marketDatalist', allPlayers, marketNames);
}

// ─── Tab: Players List ──────────────────────────────────────────────────────
function getFilteredPlayers() {
  if (allPlayers.length === 0) return [];

  const fixtureFilter = document.getElementById('playersFixtureFilter').value === 'yes';
  const minProb = parseInt(document.getElementById('playersMinProb').value) / 100;
  const minPrice = parseFloat(document.getElementById('priceRangeMin').value) || 0;
  const maxPrice = parseFloat(document.getElementById('priceRangeMax').value) || 99999;
  const filterGK = document.getElementById('filterGK').checked;
  const filterDEF = document.getElementById('filterDEF').checked;
  const filterMID = document.getElementById('filterMID').checked;
  const filterATT = document.getElementById('filterATT').checked;
  const selectedTeams = [...selectedTeamsFilter];

  let filtered = allPlayers.filter(p => {
    if (p.price < minPrice || p.price > maxPrice) return false;
    if (p.start_probability < minProb) return false;
    const posOk = (filterGK && p.position === 'GK') || (filterDEF && p.position === 'DEF') ||
                  (filterMID && p.position === 'MID') || (filterATT && p.position === 'ATT');
    if (!posOk) return false;
    if (selectedTeams.length > 0 && !selectedTeams.includes(p.team)) return false;
    return true;
  });

  // Apply fixture filter
  if (fixtureFilter) {
    filtered = filtered.filter(p => {
      if (p.position === 'GK' && p.fixture < 0.9775) return false;
      if (p.position === 'DEF' && p.fixture < 0.985) return false;
      if (p.position === 'MID' && p.fixture < 0.97) return false;
      if (p.position === 'ATT' && p.fixture < 0.96) return false;
      return true;
    });
  }

  // Sort
  const sortBy = document.getElementById('selSort').value;
  const useStartProb = document.getElementById('selWorthProb').value === 'yes';
  return sortPlayers(filtered, sortBy, useStartProb);
}

function renderPlayersTab() {
  const sorted = getFilteredPlayers();
  const container = document.getElementById('playersList');
  const countEl = document.getElementById('playersCount');

  container.innerHTML = '';
  countEl.textContent = `${sorted.length} ${t('players.found')}`;

  // Render in batches for performance
  const fragment = document.createDocumentFragment();
  for (const p of sorted) {
    fragment.appendChild(renderPlayerCard(p));
  }
  container.appendChild(fragment);
}

// ─── Tab: Budget ────────────────────────────────────────────────────────────
function tryAddBlinded() {
  const input = document.getElementById('blindedSearch');
  const name = input.value.trim();
  if (!name) return;
  const player = allPlayers.find(p => p.name === name);
  if (!player) return;
  blindedNames.add(name);
  bannedNames.delete(name);
  input.value = '';
  renderBlindedList();
  renderBannedList();
  updateAllDatalists();
  persistState();
}

function tryAddBanned() {
  const input = document.getElementById('bannedSearch');
  const name = input.value.trim();
  if (!name) return;
  const player = allPlayers.find(p => p.name === name);
  if (!player) return;
  bannedNames.add(name);
  blindedNames.delete(name);
  input.value = '';
  renderBannedList();
  renderBlindedList();
  updateAllDatalists();
  persistState();
}

function _formatPrice(val) {
  return divideMillions ? parseFloat(val.toFixed(1)) + 'M' : Math.round(val) + 'M';
}

function renderBlindedList() {
  const container = document.getElementById('blindedList');
  const totalEl = document.getElementById('blindedTotal');
  container.innerHTML = '';
  let totalPrice = 0;
  for (const name of blindedNames) {
    const p = allPlayers.find(pl => pl.name === name);
    if (!p) continue;
    totalPrice += p.price;
    const chip = document.createElement('span');
    chip.className = 'player-chip';
    chip.innerHTML = `🔒 ${name} (${_formatPrice(p.price)}) <span class="remove-chip" onclick="removeBlinded('${name.replace(/'/g, "\\'")}')">&times;</span>`;
    container.appendChild(chip);
  }
  if (blindedNames.size > 0) {
    totalEl.style.display = 'block';
    totalEl.textContent = `💰 Total: ${_formatPrice(totalPrice)}`;
  } else {
    totalEl.style.display = 'none';
  }
}

function renderBannedList() {
  const container = document.getElementById('bannedList');
  container.innerHTML = '';
  for (const name of bannedNames) {
    const chip = document.createElement('span');
    chip.className = 'player-chip';
    chip.innerHTML = `🚫 ${name} <span class="remove-chip" onclick="removeBanned('${name.replace(/'/g, "\\'")}')">&times;</span>`;
    container.appendChild(chip);
  }
}

function removeBlinded(name) { blindedNames.delete(name); renderBlindedList(); updateAllDatalists(); persistState(); }
function removeBanned(name) { bannedNames.delete(name); renderBannedList(); updateAllDatalists(); persistState(); }

// ─── Teams filter (chips) ───────────────────────────────────────────────────
function updateTeamsDatalist() {
  const dl = document.getElementById('filterTeamsDatalist');
  dl.innerHTML = '';
  for (const team of teamsList) {
    if (selectedTeamsFilter.has(team)) continue;
    const opt = document.createElement('option');
    opt.value = team;
    dl.appendChild(opt);
  }
}

function tryAddTeamFilter() {
  const input = document.getElementById('filterTeamsSearch');
  const val = input.value.trim();
  if (!val || !teamsList.includes(val) || selectedTeamsFilter.has(val)) return;
  selectedTeamsFilter.add(val);
  input.value = '';
  renderTeamChips();
  persistState();
  updateTeamsDatalist();
  renderPlayersTab();
}

function removeTeamFilter(team) {
  selectedTeamsFilter.delete(team);
  renderTeamChips();
  updateTeamsDatalist();
  persistState();
  renderPlayersTab();
}

function renderTeamChips() {
  const container = document.getElementById('filterTeamsChips');
  container.innerHTML = '';
  for (const team of selectedTeamsFilter) {
    const chip = document.createElement('span');
    chip.className = 'player-chip';
    chip.innerHTML = `${team} <span class="remove-chip" onclick="removeTeamFilter('${team.replace(/'/g, "\\'")}')">&times;</span>`;
    container.appendChild(chip);
  }
}

async function calculateBudget() {
  if (allPlayers.length === 0) { alert(t('warn.load_first')); return; }

  const comp = document.getElementById('selCompetition').value;
  const app = document.getElementById('selApp').value;
  const isBiwenger = app === 'biwenger';
  const ignoreForm = document.getElementById('selIgnoreForm').value === 'yes';
  const ignoreFixtures = document.getElementById('selIgnoreFixtures').value === 'yes';
  const ignorePenalties = document.getElementById('selPenalties').value === 'no';
  const jornadaKey = document.getElementById('selJornada')?.value || '';
  const numJornadas = parseInt(document.getElementById('selNumJornadas')?.value || '1');

  let budget = parseFloat(document.getElementById('budgetInput').value);
  if (divideMillions) budget = Math.round(budget * 10);

  const minProb = parseInt(document.getElementById('budgetMinProb').value) / 100;
  const fixtureFilter = document.getElementById('budgetFixtureFilter').value === 'yes';
  const premium = document.getElementById('budgetPremium').checked;

  let formations = [[3,4,3],[3,5,2],[4,3,3],[4,4,2],[4,5,1],[5,3,2],[5,4,1]];
  if (premium) formations = formations.concat([[3,3,4],[3,6,1],[4,2,4],[4,6,0],[5,2,3]]);

  showLoading(t('loading.calculating'), true);
  try {
    const data = await apiPostSSE('/api/calculate-stream', {
      competition: comp, app, ignore_form: ignoreForm,
      ignore_fixtures: ignoreFixtures, ignore_penalties: ignorePenalties,
      jornada_key: jornadaKey, num_jornadas: numJornadas,
      budget, blinded_names: [...blindedNames], banned_names: [...bannedNames],
      formations, min_prob: minProb, max_prob: 1.0,
      use_fixture_filter: fixtureFilter, speed_up: true,
      session_id: SESSION_ID,
    });

    const container = document.getElementById('budgetResults');
    container.innerHTML = '';

    if (!data || data.error) {
      container.innerHTML = `<p class="caption">${t('warn.not_enough')}</p>`;
    } else if (data.formations.length === 0) {
      container.innerHTML = `<p class="caption">${t('warn.not_enough')}</p>`;
    } else {
      for (const fr of data.formations) {
        container.appendChild(renderFormationResult(fr));
      }
    }
    hideLoading();
  } catch (e) {
    hideLoading();
    console.error('Error calculating:', e);
    alert('Error calculando. Asegúrate de que el servidor API está corriendo.');
  }
}

// ─── Tab: My Best 11 ────────────────────────────────────────────────────────
function addMy11Player() {
  const input = document.getElementById('my11Search');
  const name = input.value.trim();
  if (!name || my11Names.has(name)) return;
  const player = allPlayers.find(p => p.name === name);
  if (!player) return;
  my11Names.add(name);
  input.value = '';
  renderMy11List();
  updateAllDatalists();
  persistState();
}

function renderMy11List() {
  const container = document.getElementById('my11SelectedList');
  container.innerHTML = '';
  if (my11Names.size === 0) return;

  const sortBy = document.getElementById('selSort').value;
  const useStartProb = document.getElementById('selWorthProb').value === 'yes';
  let players = allPlayers.filter(p => my11Names.has(p.name));
  players = sortPlayers(players, sortBy, useStartProb);

  for (const p of players) {
    const card = renderPlayerCard(p, {
      showRemove: true,
      removeCallback: (name) => { my11Names.delete(name); my11Locked.delete(name); renderMy11List(); updateAllDatalists(); persistState(); },
      showLock: true,
      lockCallback: (name) => {
        if (my11Locked.has(name)) my11Locked.delete(name);
        else my11Locked.add(name);
        renderMy11List();
        persistState();
      },
      isLocked: my11Locked.has(p.name),
    });
    container.appendChild(card);
  }
}

// ─── Squad localStorage management ──────────────────────────────────────────
const SQUAD_STORAGE_KEY = 'cf_saved_squads';

function _getSavedSquads() {
  try { return JSON.parse(localStorage.getItem(SQUAD_STORAGE_KEY)) || []; }
  catch { return []; }
}

function _setSavedSquads(squads) {
  localStorage.setItem(SQUAD_STORAGE_KEY, JSON.stringify(squads));
}

function saveSquad() {
  if (my11Names.size === 0) return;
  const input = document.getElementById('squadNameInput');
  let name = input.value.trim();
  if (!name) {
    const now = new Date();
    name = `${now.toLocaleDateString()} ${now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
  }
  const squads = _getSavedSquads();
  const existing = squads.findIndex(s => s.name === name);
  const entry = { name, players: [...my11Names], date: new Date().toISOString() };
  if (existing >= 0) squads[existing] = entry;
  else squads.unshift(entry);
  _setSavedSquads(squads);
  input.value = '';
  renderSquadList();
  showToast(t('squad.saved_ok'));
}

function loadSquad(index) {
  const squads = _getSavedSquads();
  const squad = squads[index];
  if (!squad) return;
  my11Names.clear();
  my11Locked.clear();
  for (const name of squad.players) my11Names.add(name);
  renderMy11List();
  updateAllDatalists();
  persistState();
  showToast(`${t('squad.loaded_ok')} (${squad.players.length} ${t('squad.players_count')})`);
}

function deleteSquad(index) {
  const squads = _getSavedSquads();
  squads.splice(index, 1);
  _setSavedSquads(squads);
  renderSquadList();
  showToast(t('squad.deleted_ok'));
}

function renderSquadList() {
  const container = document.getElementById('squadList');
  if (!container) return;
  const squads = _getSavedSquads();
  if (squads.length === 0) {
    container.innerHTML = `<p class="squad-empty">${t('squad.empty')}</p>`;
    return;
  }
  container.innerHTML = '';
  squads.forEach((sq, i) => {
    const d = new Date(sq.date);
    const dateStr = d.toLocaleDateString();
    const el = document.createElement('div');
    el.className = 'squad-item';
    el.innerHTML = `
      <div class="squad-item-info">
        <div class="squad-item-name">${sq.name}</div>
        <div class="squad-item-meta">${sq.players.length} ${t('squad.players_count')} · ${dateStr}</div>
      </div>
      <div class="squad-item-actions">
        <button class="btn-small" onclick="loadSquad(${i})">${t('squad.load')}</button>
        <button class="btn-small" onclick="deleteSquad(${i})">${t('squad.delete')}</button>
      </div>`;
    container.appendChild(el);
  });
}

async function calculateMy11() {
  if (allPlayers.length === 0) { alert(t('warn.load_first')); return; }
  if (my11Names.size < 11) { alert(t('warn.need_11')); return; }

  const comp = document.getElementById('selCompetition').value;
  const app = document.getElementById('selApp').value;
  const ignoreForm = document.getElementById('selIgnoreForm').value === 'yes';
  const ignoreFixtures = document.getElementById('selIgnoreFixtures').value === 'yes';
  const ignorePenalties = document.getElementById('selPenalties').value === 'no';
  const jornadaKey = document.getElementById('selJornada')?.value || '';
  const numJornadas = parseInt(document.getElementById('selNumJornadas')?.value || '1');

  const minProb = parseInt(document.getElementById('my11MinProb').value) / 100;
  const fixtureFilter = document.getElementById('my11FixtureFilter').value === 'yes';
  const premium = document.getElementById('my11Premium').checked;

  let formations = [[3,4,3],[3,5,2],[4,3,3],[4,4,2],[4,5,1],[5,3,2],[5,4,1]];
  if (premium) formations = formations.concat([[3,3,4],[3,6,1],[4,2,4],[4,6,0],[5,2,3]]);

  showLoading(t('loading.calculating'), true);
  try {
    const data = await apiPostSSE('/api/calculate-stream', {
      competition: comp, app, ignore_form: ignoreForm,
      ignore_fixtures: ignoreFixtures, ignore_penalties: ignorePenalties,
      jornada_key: jornadaKey, num_jornadas: numJornadas,
      budget: -1, blinded_names: [...my11Locked], banned_names: [],
      formations, min_prob: minProb, max_prob: 1.0,
      use_fixture_filter: fixtureFilter, speed_up: true,
      session_id: SESSION_ID,
      selected_player_names: [...my11Names],
    });

    const container = document.getElementById('my11Results');
    container.innerHTML = '';

    if (!data || data.error || data.formations.length === 0) {
      container.innerHTML = `<p class="caption">${t('warn.not_enough')}</p>`;
    } else {
      for (const fr of data.formations) {
        container.appendChild(renderFormationResult(fr));
      }
    }
    hideLoading();
  } catch (e) {
    hideLoading();
    console.error('Error calculating:', e);
    alert('Error calculando.');
  }
}

// ─── Tab: Market ────────────────────────────────────────────────────────────
function addMarketPlayer() {
  const input = document.getElementById('marketSearch');
  const name = input.value.trim();
  if (!name || marketNames.has(name)) return;
  const player = allPlayers.find(p => p.name === name);
  if (!player) return;
  marketNames.add(name);
  input.value = '';
  renderMarketTab();
  updateAllDatalists();
  persistState();
}

function renderMarketTab() {
  const container = document.getElementById('marketSelectedList');
  const countEl = document.getElementById('marketCount');
  container.innerHTML = '';

  if (marketNames.size === 0) {
    countEl.textContent = '';
    return;
  }

  const sortBy = document.getElementById('selSort').value;
  const useStartProb = document.getElementById('selWorthProb').value === 'yes';
  let players = allPlayers.filter(p => marketNames.has(p.name));

  // Apply market filters
  const fixtureFilter = document.getElementById('marketFixtureFilter').value === 'yes';
  const minProb = parseInt(document.getElementById('marketMinProb').value) / 100;

  let filtered = players.filter(p => p.start_probability >= minProb);
  if (fixtureFilter) {
    filtered = filtered.filter(p => {
      if (p.position === 'GK' && p.fixture < 0.9775) return false;
      if (p.position === 'DEF' && p.fixture < 0.985) return false;
      if (p.position === 'MID' && p.fixture < 0.97) return false;
      if (p.position === 'ATT' && p.fixture < 0.96) return false;
      return true;
    });
  }

  filtered = sortPlayers(filtered, sortBy, useStartProb);
  const numFiltered = players.length - filtered.length;
  countEl.textContent = `${filtered.length} ${LANG === 'en' ? 'selected' : 'seleccionados'} (${numFiltered} ${LANG === 'en' ? 'filtered' : 'filtrados'})`;

  for (const p of filtered) {
    const card = renderPlayerCard(p, {
      showRemove: true,
      removeCallback: (name) => { marketNames.delete(name); renderMarketTab(); updateAllDatalists(); persistState(); },
    });
    container.appendChild(card);
  }
}

// ─── Copy to clipboard ──────────────────────────────────────────────────────
function copyPlayerNames() {
  const sorted = getFilteredPlayers();
  const text = sorted.map(p => `- ${p.name}`).join('\n');
  navigator.clipboard.writeText(text).then(() => showToast(t('toast.copied')));
}

function copyPlayersFull() {
  const sorted = getFilteredPlayers();
  const text = sorted.map(p => `- ${p.name} (${p.position}, ${p.team}): ${p.price}M - ${p.show_value} pts (${(p.start_probability*100).toFixed(0)}%)`).join('\n');
  navigator.clipboard.writeText(text).then(() => showToast(t('toast.copied')));
}

// ─── Tabs navigation ────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
  });
}

// ─── Sidebar toggle (mobile) ────────────────────────────────────────────────
function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebarToggle');
  const close = document.getElementById('sidebarClose');

  // Create backdrop
  const backdrop = document.createElement('div');
  backdrop.className = 'sidebar-backdrop';
  document.body.appendChild(backdrop);

  toggle.addEventListener('click', () => {
    sidebar.classList.add('open');
    backdrop.classList.add('visible');
  });
  close.addEventListener('click', () => {
    sidebar.classList.remove('open');
    backdrop.classList.remove('visible');
  });
  backdrop.addEventListener('click', () => {
    sidebar.classList.remove('open');
    backdrop.classList.remove('visible');
  });
}

// ─── Range input live update ────────────────────────────────────────────────
function updateRangeRightFill(input) {
  const pct = ((input.value - input.min) / (input.max - input.min)) * 100;
  input.style.background = `linear-gradient(to right, var(--bg-input) 0%, var(--bg-input) ${pct}%, var(--accent) ${pct}%, var(--accent) 100%)`;
}

function initRangeInputs() {
  const ranges = [
    ['budgetMinProb', 'budgetMinProbVal'],
    ['my11MinProb', 'my11MinProbVal'],
    ['playersMinProb', 'playersMinProbVal'],
    ['marketMinProb', 'marketMinProbVal'],
  ];
  for (const [inputId, spanId] of ranges) {
    const input = document.getElementById(inputId);
    const span = document.getElementById(spanId);
    if (input && span) {
      input.addEventListener('input', () => {
        span.textContent = input.value + '%';
        updateRangeRightFill(input);
      });
      updateRangeRightFill(input);
    }
  }
}

function initPriceRangeSlider() {
  const minEl = document.getElementById('priceRangeMin');
  const maxEl = document.getElementById('priceRangeMax');
  const fill = document.getElementById('priceRangeFill');
  const minLabel = document.getElementById('priceMinLabel');
  const maxLabel = document.getElementById('priceMaxLabel');
  if (!minEl || !maxEl) return;

  function update() {
    let lo = parseInt(minEl.value);
    let hi = parseInt(maxEl.value);
    if (lo > hi) { minEl.value = hi; lo = hi; }
    if (hi < lo) { maxEl.value = lo; hi = lo; }
    const rangeMax = parseInt(minEl.max) || 500;
    const leftPct = (lo / rangeMax) * 100;
    const rightPct = (hi / rangeMax) * 100;
    fill.style.left = leftPct + '%';
    fill.style.width = (rightPct - leftPct) + '%';
    minLabel.textContent = lo + 'M';
    maxLabel.textContent = hi + 'M';
  }

  minEl.addEventListener('input', update);
  maxEl.addEventListener('input', update);
  update();
}

function updatePriceSliderRange(maxPrice) {
  const step = maxPrice > 50 ? 1 : 0.1;
  const minEl = document.getElementById('priceRangeMin');
  const maxEl = document.getElementById('priceRangeMax');
  if (!minEl || !maxEl) return;
  const roundedMax = Math.ceil(maxPrice);
  minEl.max = roundedMax; maxEl.max = roundedMax;
  minEl.step = step; maxEl.step = step;
  minEl.value = 0; maxEl.value = roundedMax;
  initPriceRangeSlider();
}

// ─── Event listeners ────────────────────────────────────────────────────────
function initEventListeners() {
  // Load players button
  document.getElementById('btnLoadPlayers').addEventListener('click', loadPlayers);

  // Calculate buttons
  document.getElementById('btnCalcBudget').addEventListener('click', calculateBudget);
  document.getElementById('btnCalcMy11').addEventListener('click', calculateMy11);

  // Sort/filter changes -> re-render lists
  const reRenderTriggers = ['selSort', 'selWorthProb', 'playersFixtureFilter', 'playersMinProb',
    'priceRangeMin', 'priceRangeMax', 'filterGK', 'filterDEF', 'filterMID', 'filterATT'];
  for (const id of reRenderTriggers) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', renderPlayersTab);
  }

  // Sidebar settings that require reloading players
  const reloadTriggers = ['selCompetition', 'selApp', 'selJornada', 'selNumJornadas',
    'selIgnoreForm', 'selIgnoreFixtures', 'selPenalties'];
  for (const id of reloadTriggers) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => {
      if (allPlayers.length > 0) {
        allPlayers = [];
        renderPlayersTab();
        renderMarketTab();
      }
      loadPlayers();
    });
  }

  // Market filter changes
  ['marketFixtureFilter', 'marketMinProb'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', renderMarketTab);
  });

  // App change updates budget
  document.getElementById('selApp').addEventListener('change', updateBudgetInput);

  // Worth prob container visibility
  document.getElementById('selSort').addEventListener('change', () => {
    const isWorth = document.getElementById('selSort').value === 'worth';
    document.getElementById('worthProbContainer').style.display = isWorth ? 'block' : 'none';
  });

  // Auto-add on datalist selection (input event fires when user picks from datalist)
  document.getElementById('blindedSearch').addEventListener('input', tryAddBlinded);
  document.getElementById('bannedSearch').addEventListener('input', tryAddBanned);
  document.getElementById('my11Search').addEventListener('input', addMy11Player);
  document.getElementById('marketSearch').addEventListener('input', addMarketPlayer);
  document.getElementById('filterTeamsSearch').addEventListener('input', tryAddTeamFilter);

  // Enter key on search inputs (fallback)
  document.getElementById('blindedSearch').addEventListener('keydown', e => { if (e.key === 'Enter') tryAddBlinded(); });
  document.getElementById('bannedSearch').addEventListener('keydown', e => { if (e.key === 'Enter') tryAddBanned(); });
  document.getElementById('my11Search').addEventListener('keydown', e => { if (e.key === 'Enter') addMy11Player(); });
  document.getElementById('marketSearch').addEventListener('keydown', e => { if (e.key === 'Enter') addMarketPlayer(); });
  document.getElementById('filterTeamsSearch').addEventListener('keydown', e => { if (e.key === 'Enter') tryAddTeamFilter(); });

  // Persist all filter changes to localStorage
  const allFilterIds = [
    'selCompetition', 'selApp', 'selPenalties', 'selSort', 'selWorthProb',
    'selJornada', 'selNumJornadas', 'selIgnoreForm', 'selIgnoreFixtures',
    'budgetInput', 'budgetFixtureFilter', 'budgetMinProb', 'budgetPremium',
    'my11FixtureFilter', 'my11MinProb', 'my11Premium',
    'playersFixtureFilter', 'playersMinProb', 'priceRangeMin', 'priceRangeMax',
    'filterGK', 'filterDEF', 'filterMID', 'filterATT',
    'marketFixtureFilter', 'marketMinProb',
  ];
  for (const id of allFilterIds) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', persistState);
    if (el && (el.type === 'range' || el.type === 'number')) el.addEventListener('input', persistState);
  }
}

// ─── Cookie Consent / Privacy ───────────────────────────────────────────────
function initCookieConsent() {
  const banner = document.getElementById('cookieConsent');
  if (!banner) return;
  const consent = localStorage.getItem('cookie_consent');
  if (consent) {
    banner.classList.add('hidden');
    if (consent === 'accepted') {
      gtag('consent', 'update', {
        'ad_storage': 'granted',
        'ad_user_data': 'granted',
        'ad_personalization': 'granted',
        'analytics_storage': 'granted'
      });
      enableAnalytics();
    }
  }
}

function acceptCookies() {
  localStorage.setItem('cookie_consent', 'accepted');
  document.getElementById('cookieConsent')?.classList.add('hidden');
  gtag('consent', 'update', {
    'ad_storage': 'granted',
    'ad_user_data': 'granted',
    'ad_personalization': 'granted',
    'analytics_storage': 'granted'
  });
  enableAnalytics();
}

function rejectCookies() {
  localStorage.setItem('cookie_consent', 'rejected');
  document.getElementById('cookieConsent')?.classList.add('hidden');
  gtag('consent', 'update', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied'
  });
}

function enableAnalytics() {
  // Google Analytics – only load after consent
  if (window.gtag) return; // already loaded
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://www.googletagmanager.com/gtag/js?id=G-QXF4YKPSMD';
  document.head.appendChild(script);
  script.onload = () => {
    window.dataLayer = window.dataLayer || [];
    function gtag(){ dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', 'G-QXF4YKPSMD');
  };
}

function openPrivacyFromApp() {
  document.getElementById('privacyModal')?.classList.add('visible');
}

function closePrivacyFromApp() {
  document.getElementById('privacyModal')?.classList.remove('visible');
}

function resetCookieConsent() {
  localStorage.removeItem('cookie_consent');
  const banner = document.getElementById('cookieConsent');
  if (banner) banner.classList.remove('hidden');
}

function applyCookieI18N() {
  const ids = {
    cookieText: 'cookie.text', cookiePrivacyLink: 'cookie.privacy',
    cookieAccept: 'cookie.accept', cookieReject: 'cookie.reject',
    privacyTitle: 'privacy.title', privacyP1: 'privacy.p1',
    privacyP2: 'privacy.p2', privacyP3: 'privacy.p3',
    privacyClose: 'privacy.close',
  };
  for (const [elId, key] of Object.entries(ids)) {
    const el = document.getElementById(elId);
    if (el) el.textContent = t(key);
  }
  const p4 = document.getElementById('privacyP4');
  if (p4) {
    p4.innerHTML = `${t('privacy.p4')} <a href="mailto:calculadora.fantasy@gmail.com" style="color:var(--accent)">calculadora.fantasy@gmail.com</a>.`;
  }
}

// ─── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initLang();
  applyI18N();
  applyCookieI18N();
  initTabs();
  initSidebar();
  initRangeInputs();
  initPriceRangeSlider();
  initEventListeners();
  initCookieConsent();
  renderSquadList();
  loadCompetitions();

  // Initial worth prob visibility
  document.getElementById('worthProbContainer').style.display = 'none';

  // Track page visit
  apiPost('/api/visit', {
    session_id: SESSION_ID,
    page: 'app',
    lang: LANG,
    referrer: document.referrer || '',
    screen_w: window.screen?.width,
    screen_h: window.screen?.height,
  }).catch(() => {});
});
