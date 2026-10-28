'use strict';
/* Campus Route Planner — web GUI. Talks to the local Python server (src/gui/server.py). */
(() => {
  const W = 1000, H = 640, R = 17, CURVE = 26;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const LABEL = { ucs: 'UCS', astar: 'A*' };

  // ---------- helpers ----------
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const fmt = (n) => (n === null || n === undefined ? '–' : Number.isInteger(n) ? String(n) : String(+n.toFixed(2)));

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else node.setAttribute(k, v === true ? '' : v);
    }
    for (const child of [].concat(children)) {
      if (child === null || child === undefined) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function svg(tag, attrs = {}, parent) {
    const node = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
  }

  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
    del(key) { try { localStorage.removeItem(key); } catch { /* ignore */ } },
  };

  async function call(url, body) {
    const options = body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    };
    const res = await fetch(url, options);
    let data = {};
    try { data = await res.json(); } catch { /* empty body */ }
    if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { code: data.code });
    return data;
  }

  function toast(message, kind = 'info', ms = 4500) {
    const t = el('div', { class: `toast ${kind}` }, message);
    $('#toasts').append(t);
    requestAnimationFrame(() => t.classList.add('in'));
    setTimeout(() => { t.classList.remove('in'); setTimeout(() => t.remove(), 350); }, ms);
  }

  // ---------- state ----------
  const S = {
    datasets: [], dataset: null, graph: null, pos: {},
    req: { start: '', goal: '', required: '', blocked: new Set() },
    vmax: 80, result: null, error: null,
    view: store.get('crp:view') || 'astar',
    step: 0, playing: false, speed: 1, timer: null,
    showH: false, showWeights: true, pick: null,
    routeShown: {},
  };
  const runOf = (algo) => S.result?.runs.find((r) => r.algorithm === algo) || null;
  const viewAlgos = () => (S.view === 'race' ? ['ucs', 'astar'] : [S.view]);
  const maxSteps = () => Math.max(0, ...viewAlgos().map((a) => runOf(a)?.trace.length || 0));
  const key = (u, v) => `${u}>${v}`;

  // ---------- layout ----------
  function normalize(raw) {
    const ids = Object.keys(raw);
    if (!ids.length) return {};
    const xs = ids.map((id) => raw[id].x), ys = ids.map((id) => raw[id].y);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const w = maxX - minX || 1, h = maxY - minY || 1, padX = 80, padY = 70;
    const s = Math.min((W - 2 * padX) / w, (H - 2 * padY) / h);
    const ox = (W - w * s) / 2, oy = (H - h * s) / 2;
    return Object.fromEntries(ids.map((id) => [id, { x: ox + (raw[id].x - minX) * s, y: oy + (raw[id].y - minY) * s }]));
  }

  /* Graphs without coordinates: layered start (BFS along the edges, left to right), then a few hundred
     deterministic force-directed iterations to spread the buildings. */
  function autoLayout(nodes, edges) {
    const ids = nodes.map((n) => n.id);
    const out = new Map(ids.map((id) => [id, []])), inn = new Map(ids.map((id) => [id, []]));
    for (const e of edges) {
      if (e.source === e.target) continue;
      out.get(e.source).push(e.target);
      inn.get(e.target).push(e.source);
    }
    const seen = new Set(), comps = [];
    for (const id of ids) {
      if (seen.has(id)) continue;
      const list = [], queue = [id];
      seen.add(id);
      while (queue.length) {
        const u = queue.shift();
        list.push(u);
        for (const v of [...out.get(u), ...inn.get(u)]) if (!seen.has(v)) { seen.add(v); queue.push(v); }
      }
      comps.push(list);
    }
    comps.sort((a, b) => b.length - a.length);

    // Each connected piece is laid out on its own, then the pieces are placed side by side
    // (otherwise repulsion pushes a small island far away and squeezes the main map).
    const result = {};
    let offsetX = 0;
    for (const list of comps) {
      const local = layoutComponent(list, out, inn, edges);
      const xs = list.map((id) => local[id].x), ys = list.map((id) => local[id].y);
      const minX = Math.min(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
      for (const id of list) result[id] = { x: local[id].x - minX + offsetX, y: local[id].y - (minY + maxY) / 2 };
      offsetX += Math.max(...xs) - minX + 200;
    }
    return result;
  }

  function layoutComponent(list, out, inn, edges) {
    const root = list.reduce((best, id) => (inn.get(id).length < inn.get(best).length ? id : best), list[0]);
    const layer = new Map([[root, 0]]);
    const queue = [root];
    while (queue.length) {
      const u = queue.shift();
      for (const v of out.get(u)) if (!layer.has(v)) { layer.set(v, layer.get(u) + 1); queue.push(v); }
    }
    let changed = true;
    while (changed) {
      changed = false;
      for (const id of list) {
        if (layer.has(id)) continue;
        const pred = inn.get(id).find((v) => layer.has(v));
        const succ = out.get(id).find((v) => layer.has(v));
        if (pred !== undefined) { layer.set(id, layer.get(pred) + 1); changed = true; }
        else if (succ !== undefined) { layer.set(id, layer.get(succ) - 1); changed = true; }
      }
    }
    const min = Math.min(...layer.values());
    const cols = new Map();
    for (const id of list) {
      const l = layer.get(id) - min;
      if (!cols.has(l)) cols.set(l, []);
      cols.get(l).push(id);
    }
    const pos = {};
    for (const [l, col] of cols) {
      col.forEach((id, i) => { pos[id] = { x: l * 190, y: (i - (col.length - 1) / 2) * 130 }; });
    }

    const ids = list, index = new Map(ids.map((id, i) => [id, i]));
    const P = ids.map((id) => ({ ...pos[id] })), n = ids.length, anchor = P.map((p) => p.x);
    const links = [], linked = new Set();
    for (const e of edges) {
      const a = index.get(e.source), b = index.get(e.target);
      if (a === undefined || b === undefined) continue;
      const k = `${Math.min(a, b)}-${Math.max(a, b)}`;
      if (a !== b && !linked.has(k)) { linked.add(k); links.push([a, b]); }
    }
    const L = 165;
    let temp = 50;
    for (let it = 0; it < 320; it++) {
      const D = P.map(() => ({ x: 0, y: 0 }));
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = P[i].x - P[j].x, dy = P[i].y - P[j].y, d = Math.hypot(dx, dy);
          if (d < 0.01) { dx = 0.1 * (i - j); dy = 0.1; d = Math.hypot(dx, dy); }
          const f = (L * L) / d;
          D[i].x += (dx / d) * f; D[i].y += (dy / d) * f;
          D[j].x -= (dx / d) * f; D[j].y -= (dy / d) * f;
        }
      }
      for (const [a, b] of links) {
        const dx = P[a].x - P[b].x, dy = P[a].y - P[b].y, d = Math.hypot(dx, dy) || 0.01, f = (d * d) / L;
        D[a].x -= (dx / d) * f; D[a].y -= (dy / d) * f;
        D[b].x += (dx / d) * f; D[b].y += (dy / d) * f;
      }
      for (let i = 0; i < n; i++) {
        D[i].x += (anchor[i] - P[i].x) * 0.6;
        const d = Math.hypot(D[i].x, D[i].y) || 1, m = Math.min(d, temp);
        P[i].x += (D[i].x / d) * m;
        P[i].y += (D[i].y / d) * m;
      }
      temp = Math.max(1.5, temp * 0.985);
    }
    return Object.fromEntries(ids.map((id, i) => [id, P[i]]));
  }

  function layoutFor(graph, fresh = false) {
    const saved = fresh ? null : store.get(`crp:pos:${graph.id}`);
    const ids = graph.nodes.map((n) => n.id);
    if (saved && ids.every((id) => saved[id]) && Object.keys(saved).length === ids.length) return saved;
    const raw = graph.coordinates
      ? Object.fromEntries(graph.nodes.map((n) => [n.id, { x: n.x, y: n.y }]))
      : autoLayout(graph.nodes, graph.edges);
    return normalize(raw);
  }

  // ---------- geometry ----------
  /* Edges between a and b; `curve` bends the line to its left (so the two directions of a pair separate). */
  function geom(a, b, curve, trim) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len;
    const nx = -uy, ny = ux;
    if (!curve) {
      const r0 = trim ? R + 3 : 0, r1 = trim ? R + 4 : 0;
      const s = { x: a.x + ux * r0, y: a.y + uy * r0 }, e = { x: b.x - ux * r1, y: b.y - uy * r1 };
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      const side = ny > 0 || (ny === 0 && nx > 0) ? -1 : 1;  // put labels above the line
      return {
        d: `M${s.x.toFixed(1)},${s.y.toFixed(1)} L${e.x.toFixed(1)},${e.y.toFixed(1)}`,
        mid,
        label: { x: mid.x + nx * 13 * side, y: mid.y + ny * 13 * side },
      };
    }
    const c = { x: (a.x + b.x) / 2 + nx * curve, y: (a.y + b.y) / 2 + ny * curve };
    const toward = (p, r) => {
      const ddx = c.x - p.x, ddy = c.y - p.y, l = Math.hypot(ddx, ddy) || 1;
      return { x: p.x + (ddx / l) * r, y: p.y + (ddy / l) * r };
    };
    const s = trim ? toward(a, R + 3) : a, e = trim ? toward(b, R + 4) : b;
    const mid = { x: (s.x + 2 * c.x + e.x) / 4, y: (s.y + 2 * c.y + e.y) / 4 };
    return {
      d: `M${s.x.toFixed(1)},${s.y.toFixed(1)} Q${c.x.toFixed(1)},${c.y.toFixed(1)} ${e.x.toFixed(1)},${e.y.toFixed(1)}`,
      mid,
      label: { x: mid.x + nx * 14, y: mid.y + ny * 14 },
    };
  }

  /* Two-way pairs with equal times and no single-direction closure are drawn as one line (like the brief's
     drawings); everything else as arrows, pairs as two curved arrows. */
  function edgeGroups() {
    const weights = new Map();
    for (const e of S.graph.edges) {
      if (e.source === e.target) continue;
      const k = key(e.source, e.target);
      weights.set(k, Math.min(weights.get(k) ?? Infinity, e.weight));
    }
    const done = new Set(), groups = [];
    for (const [k, w] of weights) {
      if (done.has(k)) continue;
      done.add(k);
      const [u, v] = k.split('>'), rk = key(v, u);
      if (weights.has(rk)) {
        done.add(rk);
        const w2 = weights.get(rk);
        const oneClosed = S.req.blocked.has(k) !== S.req.blocked.has(rk);
        if (w === w2 && !oneClosed) groups.push({ type: 'two', u, v, w, keys: [k, rk] });
        else groups.push({ type: 'arc', u, v, w, key: k }, { type: 'arc', u: v, v: u, w: w2, key: rk });
      } else {
        groups.push({ type: 'one', u, v, w, key: k });
      }
    }
    return groups;
  }

  function roles(id) {
    const r = [];
    if (id === S.req.start) r.push('start');
    if (id === S.req.required) r.push('stop');
    if (id === S.req.goal) r.push('goal');
    return r;
  }

  // ---------- map rendering ----------
  function render() {
    hideTooltip();
    const maps = $('#maps');
    maps.innerHTML = '';
    maps.className = `maps${S.view === 'race' ? ' race' : ''}`;
    if (!S.graph) return;
    for (const algo of viewAlgos()) maps.append(buildMapCard(algo));
    applySteps();
  }

  let renderQueued = false;
  function scheduleRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => { renderQueued = false; render(); });
  }

  function buildMapCard(algo) {
    const run = runOf(algo);
    let sub = algo === 'ucs' ? 'uniform cost · h = 0' : `h = distance / ${S.vmax} m/min`;
    if (algo === 'astar' && run && run.heuristic === 'zero') sub = 'h = 0 (fallback)';
    const card = el('div', { class: `map-card ${algo}` }, [
      el('div', { class: 'map-head' }, [
        el('span', { class: `algo-badge ${algo}` }, LABEL[algo]),
        el('span', { class: 'map-sub' }, sub),
        el('span', { class: 'counter' }),
      ]),
    ]);
    const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'map', role: 'img', 'aria-label': `Campus map (${LABEL[algo]})` });
    card.append(s);
    drawMap(s, algo, run);

    const legend = el('div', { class: 'map-legend' }, [
      el('span', {}, [el('i', { class: 'lg-line' }), 'path']),
      el('span', {}, [el('i', { class: 'lg-line closed' }), 'closed']),
      el('span', {}, [el('i', { class: 'lg-line route' }), 'route']),
      S.req.required ? el('span', {}, [el('i', { class: 'lg-ring p' }), 'state before stop']) : null,
      el('span', {}, [el('i', { class: 'lg-ring d' }), S.req.required ? 'state after stop' : 'expanded state']),
    ]);
    card.append(legend, el('div', { class: 'map-overlay' }, [el('strong'), el('span')]));
    card._algo = algo;
    return card;
  }

  function drawMap(s, algo, run) {
    const id = (x) => `${algo}-${x}`;
    const defs = svg('defs', {}, s);
    const pattern = svg('pattern', { id: id('grid'), width: 28, height: 28, patternUnits: 'userSpaceOnUse' }, defs);
    svg('circle', { cx: 1.5, cy: 1.5, r: 1.3, class: 'grid-dot' }, pattern);
    for (const [name, cls] of [['arrow', 'arrow'], ['arrow-blocked', 'arrow-blocked']]) {
      const m = svg('marker', { id: id(name), viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 11, markerHeight: 11, markerUnits: 'userSpaceOnUse', orient: 'auto-start-reverse' }, defs);
      svg('path', { d: 'M0,0 L10,5 L0,10 z', class: cls }, m);
    }
    const startP = S.pos[S.req.start], goalP = S.pos[S.req.goal];
    if (startP && goalP) {
      const grad = svg('linearGradient', { id: id('route'), gradientUnits: 'userSpaceOnUse', x1: startP.x, y1: startP.y, x2: goalP.x, y2: goalP.y }, defs);
      const css = getComputedStyle(document.documentElement);
      [['0', '--emerald'], ['.45', '--cyan'], ['.75', '--violet'], ['1', '--rose']].forEach(([o, v]) =>
        svg('stop', { offset: o, 'stop-color': css.getPropertyValue(v).trim() }, grad));
    }
    svg('rect', { width: W, height: H, fill: `url(#${id('grid')})` }, s);

    const gEdges = svg('g', {}, s), gRoute = svg('g', { class: 'route' }, s), gNodes = svg('g', {}, s);
    const groups = edgeGroups();
    const arcs = new Set(groups.filter((g) => g.type === 'arc').map((g) => g.key));

    for (const g of groups) {
      const a = S.pos[g.u], b = S.pos[g.v];
      if (!a || !b) continue;
      const geo = geom(a, b, g.type === 'arc' ? CURVE : 0, true);
      const blocked = g.type === 'two' ? g.keys.every((k) => S.req.blocked.has(k)) : S.req.blocked.has(g.key);
      const grp = svg('g', { class: `edge ${g.type}${blocked ? ' blocked' : ''}` }, gEdges);
      svg('path', { d: geo.d, class: 'edge-line', 'marker-end': g.type === 'two' ? null : `url(#${id(blocked ? 'arrow-blocked' : 'arrow')})` }, grp);
      svg('path', { d: geo.d, class: 'edge-hit' }, grp);
      if (blocked) {
        const m = geo.mid;
        svg('circle', { cx: m.x, cy: m.y, r: 9, class: 'edge-x-bg' }, grp);
        svg('path', { d: `M${m.x - 4},${m.y - 4} L${m.x + 4},${m.y + 4} M${m.x + 4},${m.y - 4} L${m.x - 4},${m.y + 4}`, class: 'edge-x' }, grp);
      }
      if (S.showWeights && !(blocked && g.type === 'two')) {
        const t = svg('text', { x: geo.label.x, y: geo.label.y, class: 'edge-label' }, grp);
        t.textContent = fmt(g.w);
      }
      grp.addEventListener('click', (ev) => onEdgeClick(ev, g));
    }

    if (run && run.path.length > 1) {
      const d = run.path.slice(1).map((v, i) => {
        const u = run.path[i];
        return geom(S.pos[u], S.pos[v], arcs.has(key(u, v)) ? CURVE : 0, false).d;
      }).join(' ');
      svg('path', { d, class: 'route-glow', pathLength: 1 }, gRoute);
      svg('path', { d, class: 'route-line', pathLength: 1, stroke: `url(#${id('route')})` }, gRoute);
      const walker = svg('circle', { r: 6, class: 'walker' }, gRoute);
      svg('animateMotion', { dur: `${clamp(run.path.length * 0.8, 2.4, 9)}s`, repeatCount: 'indefinite', path: d, rotate: 'auto' }, walker);
    }

    const rings = new Map(), nodes = new Map();
    const h = algo === 'astar' && S.showH && run && run.heuristic === 'euclidean' ? run.h : null;
    for (const n of S.graph.nodes) {
      const p = S.pos[n.id];
      if (!p) continue;
      const r = roles(n.id);
      const g = svg('g', { class: `node ${r.join(' ')}`, transform: `translate(${p.x.toFixed(1)},${p.y.toFixed(1)})`, tabindex: 0 }, gNodes);
      rings.set(`${n.id}|1`, svg('circle', { r: R + 13, class: 'ring d' }, g));
      rings.set(`${n.id}|0`, svg('circle', { r: R + 7, class: 'ring p' }, g));
      svg('circle', { r: R, class: 'core' }, g);
      svg('circle', { r: 4.5, class: 'pip' }, g);
      const label = svg('text', { y: R + 26, class: 'node-label' }, g);
      label.textContent = n.id;
      if (r.length) {
        const text = r.map((x) => x.toUpperCase()).join(' · '), w = text.length * 6.6 + 14;
        const badge = svg('g', { class: `role-badge ${r.length > 1 ? 'multi' : r[0]}`, transform: `translate(0,${-(R + 21)})` }, g);
        svg('rect', { x: -w / 2, y: -9, width: w, height: 18, rx: 7 }, badge);
        svg('text', {}, badge).textContent = text;
      }
      if (h && h[n.id] !== undefined) {
        const text = `h ${fmt(h[n.id])}`, w = text.length * 6.6 + 12;
        const badge = svg('g', { class: 'h-badge', transform: `translate(${R + 8 + w / 2},${-R + 2})` }, g);
        svg('rect', { x: -w / 2, y: -9, width: w, height: 18, rx: 6 }, badge);
        svg('text', {}, badge).textContent = text;
      }
      nodes.set(n.id, g);
      attachNodeHandlers(g, n.id, s, algo);
    }
    s._refs = { rings, nodes, route: gRoute };
  }

  // ---------- replay ----------
  function applySteps() {
    for (const card of $$('.map-card', $('#maps'))) {
      const algo = card._algo, run = runOf(algo), refs = $('svg', card)._refs;
      const trace = run ? run.trace : [];
      const k = Math.min(S.step, trace.length);
      for (const ring of refs.rings.values()) ring.classList.remove('lit', 'current');
      for (const g of refs.nodes.values()) g.classList.remove('visited', 'reached');
      for (let i = 0; i < k; i++) {
        const t = trace[i];
        const ring = refs.rings.get(`${t.node}|${t.done ? 1 : 0}`);
        if (ring) { ring.classList.add('lit'); if (i === k - 1 && k < trace.length) ring.classList.add('current'); }
        refs.nodes.get(t.node)?.classList.add('visited');
      }
      const finished = !!run && k >= trace.length;
      const success = finished && run.status === 'SUCCESS';
      refs.route.classList.toggle('show', success);
      if (success) {
        if (S.routeShown[algo]) refs.route.classList.add('static');
        else drawRoute(refs.route);
        S.routeShown[algo] = true;
        refs.nodes.get(S.req.goal)?.classList.add('reached');
      } else {
        refs.route.classList.remove('static');
        S.routeShown[algo] = false;
      }

      const counter = $('.counter', card);
      counter.innerHTML = '';
      counter.append('expanded ', el('b', {}, String(k)), ` / ${trace.length}`);

      const overlay = $('.map-overlay', card);
      let title = '', text = '';
      if (S.error) { title = 'Invalid request'; text = S.error; }
      else if (!S.req.start || !S.req.goal) { title = 'Choose a start and a goal'; text = 'Use the panel on the left, or click a building.'; }
      else if (finished && run.status !== 'SUCCESS') {
        title = 'NO_FEASIBLE_ROUTE';
        text = S.req.required ? 'No route visits the required stop and then reaches the goal.' : 'The goal cannot be reached with these closures.';
      }
      $('strong', overlay).textContent = title;
      $('span', overlay).textContent = text;
      overlay.classList.toggle('show', !!title);
      overlay.classList.toggle('bad', !!S.error || (finished && run.status !== 'SUCCESS'));
    }
    updateRaceWinner();
    updateScrub();
  }

  /* "Draws" the route from start to goal with a dash-offset transition, then removes the dash so the
     final state never depends on the animation having run. */
  function drawRoute(group) {
    for (const path of $$('.route-line, .route-glow', group)) {
      path.style.transition = 'none';
      path.style.strokeDasharray = '1 1';
      path.style.strokeDashoffset = '1';
      path.getBoundingClientRect();
      path.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.2,.8,.2,1)';
      path.style.strokeDashoffset = '0';
      const done = () => { path.style.strokeDasharray = ''; path.style.strokeDashoffset = ''; path.style.transition = ''; };
      path.addEventListener('transitionend', done, { once: true });
      setTimeout(done, 1600);
    }
  }

  function updateRaceWinner() {
    $$('.map-winner').forEach((w) => w.remove());
    if (S.view !== 'race' || !S.result) return;
    const [u, a] = [runOf('ucs'), runOf('astar')];
    if (!u || !a || u.status !== 'SUCCESS' || S.step < Math.min(u.trace.length, a.trace.length)) return;
    if (u.trace.length === a.trace.length) return;
    const winner = a.trace.length < u.trace.length ? 'astar' : 'ucs';
    const diff = Math.abs(u.trace.length - a.trace.length);
    const card = $(`.map-card.${winner}`);
    card?.append(el('div', { class: 'map-winner' }, `⚡ goal reached ${diff} expansion${diff === 1 ? '' : 's'} sooner`));
  }

  function updateScrub() {
    const scrub = $('#scrub'), max = maxSteps();
    scrub.max = max;
    scrub.value = Math.min(S.step, max);
    scrub.style.setProperty('--fill', `${max ? (Math.min(S.step, max) / max) * 100 : 0}%`);
    $('#stepLabel').textContent = `${Math.min(S.step, max)} / ${max}`;
    $('#play').textContent = S.playing ? '❚❚' : '▶';
  }

  function play() {
    if (!S.result) return;
    if (S.step >= maxSteps()) S.step = 0;
    S.playing = true;
    tick(true);
  }
  function tick(first = false) {
    clearTimeout(S.timer);
    if (!S.playing) return;
    if (S.step >= maxSteps()) { S.playing = false; updateScrub(); return; }
    if (!first || S.step === 0) S.step++;
    applySteps();
    S.timer = setTimeout(tick, 430 / S.speed);
  }
  function pause() { S.playing = false; clearTimeout(S.timer); updateScrub(); }
  function seek(step) { pause(); S.step = clamp(step, 0, maxSteps()); applySteps(); }

  // ---------- solving ----------
  let solveSeq = 0, solveTimer = null;
  function solveSoon(delay = 160) { clearTimeout(solveTimer); solveTimer = setTimeout(solve, delay); }

  async function solve() {
    const { start, goal, required, blocked } = S.req;
    pause();
    if (!S.graph || !start || !goal) {
      S.result = null; S.error = null; S.step = 0;
      render(); renderResults(); renderHeuristic(); highlightTask();
      return;
    }
    const seq = ++solveSeq;
    try {
      const data = await call('/api/solve', {
        id: S.dataset, start, goal, required: required || null,
        blocked: [...blocked].map((k) => k.split('>')), vmax: S.vmax,
      });
      if (seq !== solveSeq) return;
      S.result = data; S.error = null;
      data.warnings.forEach((w) => toast(w, 'warn'));
    } catch (err) {
      if (seq !== solveSeq) return;
      S.result = null; S.error = err.message;
      toast(err.message, 'error');
    }
    S.routeShown = {}; S.step = 0;
    render(); renderResults(); renderHeuristic(); highlightTask();
    if (S.result) setTimeout(play, 250);
  }

  // ---------- panels ----------
  function renderResults() {
    const box = $('#results');
    box.innerHTML = '';
    if (S.error) {
      box.append(el('div', { class: 'result-empty' }, [el('b', {}, 'Invalid request: '), S.error]));
      return;
    }
    if (!S.result) {
      box.append(el('div', { class: 'result-empty' }, 'Choose a start and a goal to plan a route.'));
      return;
    }
    for (const run of S.result.runs) box.append(resultCard(run));
    box.append(compareCard());
  }

  function resultCard(run) {
    const ok = run.status === 'SUCCESS';
    const chips = el('div', { class: 'route-chips' });
    if (ok) {
      run.path.forEach((n, i) => {
        if (i) chips.append(el('span', { class: 'arr' }, '→'));
        chips.append(el('span', { class: `stopc${n === S.req.required ? ' req' : ''}` }, n));
      });
    } else {
      chips.append(el('span', { class: 'faint' }, 'No route satisfies the request.'));
    }
    const note = run.algorithm === 'ucs'
      ? 'Expands states by path cost g only.'
      : run.heuristic === 'euclidean'
        ? `f = g + h, h = straight-line distance / ${S.vmax} m/min.`
        : `h = 0 → ${run.heuristic_note || 'same as UCS'}`;
    return el('div', { class: `result-card ${run.algorithm}` }, [
      el('div', { class: 'rc-head' }, [
        el('span', { class: `algo-badge ${run.algorithm}` }, run.label),
        el('span', { class: `pill ${run.status}` }, run.status),
      ]),
      el('div', { class: 'metrics' }, [
        el('div', { class: 'metric' }, [el('b', {}, ok ? fmt(run.cost) : '–'), el('span', {}, 'minutes')]),
        el('div', { class: 'metric' }, [el('b', {}, String(run.expanded)), el('span', {}, 'expanded states')]),
        el('div', { class: 'metric' }, [el('b', {}, run.runtime_ms.toFixed(3)), el('span', {}, 'runtime (ms)')]),
      ]),
      chips,
      el('div', { class: 'rc-note' }, note),
    ]);
  }

  function compareCard() {
    const [u, a] = [runOf('ucs'), runOf('astar')];
    const max = Math.max(u.expanded, a.expanded, 1);
    const bar = (run) => el('div', { class: 'bar-row' }, [
      el('span', {}, run.label),
      el('div', { class: 'bar-track' }, el('div', { class: `bar-fill ${run.algorithm}`, style: `width:${(run.expanded / max) * 100}%` })),
      el('b', {}, String(run.expanded)),
    ]);
    let verdict;
    if (u.status !== a.status || u.cost !== a.cost) {
      verdict = [el('b', {}, 'Warning: '), 'the two algorithms disagree — this should never happen.'];
    } else if (a.heuristic === 'zero') {
      verdict = ['Same effort: A* has no usable heuristic here, so ', el('b', {}, 'A* with h = 0 is exactly UCS'), '.'];
    } else if (a.expanded < u.expanded) {
      const pct = Math.round((1 - a.expanded / u.expanded) * 100);
      verdict = ['Same ', el('b', {}, u.status === 'SUCCESS' ? `${fmt(u.cost)}-minute route` : 'answer'), `, but A* expanded `,
        el('b', {}, `${u.expanded - a.expanded} fewer states (−${pct}%)`), ' thanks to the heuristic.'];
    } else {
      verdict = ['Same answer and the same number of expanded states: the heuristic did not help on this request.'];
    }
    return el('div', { class: 'result-card compare' }, [
      el('div', { class: 'rc-head' }, [el('span', { class: 'badge' }, 'Expanded states')]),
      el('div', { class: 'bars' }, [bar(u), bar(a)]),
      el('div', { class: 'verdict' }, verdict),
    ]);
  }

  function renderHeuristic() {
    const status = $('#heuristicStatus'), badge = $('#heuristicBadge');
    const vmax = $('#vmax');
    vmax.style.setProperty('--fill', `${((S.vmax - vmax.min) / (vmax.max - vmax.min)) * 100}%`);
    $('#vmaxOut').textContent = `${S.vmax} m/min`;
    status.innerHTML = '';
    if (!S.graph) return;
    const check = S.graph.speed_check;
    if (!S.graph.coordinates) {
      badge.textContent = 'h = 0'; badge.className = 'badge warn';
      status.append(el('span', { class: 'warn' }, 'No coordinates for this map. '), 'A* falls back to ',
        el('b', {}, 'h = 0'), ' and behaves exactly like UCS.');
      vmax.disabled = true;
      return;
    }
    vmax.disabled = false;
    if (check.speed === null) {
      badge.textContent = 'h = 0'; badge.className = 'badge warn';
      status.append(el('span', { class: 'warn' }, `Edge ${check.edge.replace('>', ' → ')} takes 0 minutes. `),
        'No speed limit makes the straight-line heuristic safe, so A* uses ', el('b', {}, 'h = 0'), '.');
    } else if (S.vmax >= check.speed) {
      badge.textContent = 'admissible ✓'; badge.className = 'badge ok';
      status.append(el('span', { class: 'ok' }, 'Safe. '), 'Fastest edge in the data: ',
        el('b', {}, `${check.edge.replace('>', ' → ')} at ${check.speed} m/min`), ` ≤ ${S.vmax}. The heuristic never overestimates.`);
    } else {
      badge.textContent = 'h = 0'; badge.className = 'badge warn';
      status.append(el('span', { class: 'warn' }, 'Unsafe. '), `${check.edge.replace('>', ' → ')} implies `,
        el('b', {}, `${check.speed} m/min > ${S.vmax}`), ', so distance / v', el('sub', {}, 'max'),
        ' could overestimate. A* falls back to ', el('b', {}, 'h = 0'), '.');
    }
  }

  function fillSelects() {
    const ids = S.graph.nodes.map((n) => n.id).sort((a, b) => a.localeCompare(b));
    for (const [sel, none] of [['#start', '— choose —'], ['#goal', '— choose —'], ['#required', 'none']]) {
      const s = $(sel);
      s.innerHTML = '';
      s.append(el('option', { value: '' }, none));
      ids.forEach((id) => s.append(el('option', { value: id }, id)));
    }
  }

  function syncRequestUI() {
    $('#start').value = S.req.start;
    $('#goal').value = S.req.goal;
    $('#required').value = S.req.required;
    const list = $('#blockedList');
    list.innerHTML = '';
    if (!S.req.blocked.size) list.append(el('span', { class: 'empty' }, 'none — every path is open'));
    for (const k of S.req.blocked) {
      const [u, v] = k.split('>');
      const x = el('button', { type: 'button', title: 'Reopen' }, '×');
      x.addEventListener('click', () => { S.req.blocked.delete(k); syncRequestUI(); solveSoon(0); });
      list.append(el('span', { class: 'chip' }, [`${u} → ${v}`, x]));
    }
  }

  function renderMeta() {
    const d = S.datasets.find((x) => x.id === S.dataset);
    $('#datasetMeta').textContent = d
      ? `${d.buildings} buildings · ${d.edges} directed edges · ${d.coordinates ? 'coordinates ✓' : 'no coordinates'} · ${d.tasks} requests`
      : '';
  }

  function renderTasks() {
    const list = $('#taskList');
    list.innerHTML = '';
    $('#taskCount').textContent = String(S.graph.tasks.length);
    if (!S.graph.tasks.length) list.append(el('p', { class: 'hint' }, 'This map has no tasks.csv.'));
    for (const t of S.graph.tasks) {
      const tags = [
        ...t.blocked.map(([u, v]) => el('span', { class: 'tag closed' }, `✕ ${u}>${v}`)),
        t.required ? el('span', { class: 'tag via' }, `via ${t.required}`) : null,
      ];
      const b = el('button', { class: 'task', type: 'button' }, [
        el('div', { class: 't-top' }, [el('span', {}, t.id)]),
        el('div', { class: 't-route' }, `${t.start} → ${t.goal}`),
        tags.some(Boolean) ? el('div', { class: 't-tags' }, tags) : null,
      ]);
      b._task = t;
      b.addEventListener('click', () => applyTask(t));
      list.append(b);
    }
    highlightTask();
  }

  function highlightTask() {
    for (const b of $$('.task')) {
      const t = b._task;
      const same = t.start === S.req.start && t.goal === S.req.goal && (t.required || '') === S.req.required
        && t.blocked.length === S.req.blocked.size && t.blocked.every(([u, v]) => S.req.blocked.has(key(u, v)));
      b.classList.toggle('active', same);
    }
  }

  function applyTask(t) {
    S.req = { start: t.start, goal: t.goal, required: t.required || '', blocked: new Set(t.blocked.map(([u, v]) => key(u, v))) };
    syncRequestUI();
    solveSoon(0);
  }

  // ---------- datasets ----------
  async function loadDatasets(selectId) {
    const { datasets } = await call('/api/datasets');
    S.datasets = datasets;
    const sel = $('#dataset');
    sel.innerHTML = '';
    const groups = {};
    for (const d of datasets) (groups[d.group] ||= []).push(d);
    for (const [group, list] of Object.entries(groups)) {
      const og = el('optgroup', { label: group });
      list.forEach((d) => og.append(el('option', { value: d.id, disabled: !!d.error }, d.error ? `${d.name} (invalid)` : d.name)));
      sel.append(og);
    }
    const hash = decodeURIComponent(location.hash.slice(1));
    const wanted = [selectId, hash, store.get('crp:dataset')].find((x) => x && datasets.some((d) => d.id === x && !d.error));
    const pick = wanted || datasets.find((d) => !d.error)?.id;
    if (pick) await selectDataset(pick);
    datasets.filter((d) => d.error && d.group !== 'Provided').forEach((d) => toast(`${d.name}: ${d.error}`, 'error'));
  }

  async function selectDataset(id) {
    try {
      const graph = await call(`/api/graph?id=${encodeURIComponent(id)}&vmax=${S.vmax}`);
      S.dataset = id; S.graph = graph;
      $('#dataset').value = id;
      store.set('crp:dataset', id);
      history.replaceState(null, '', `#${encodeURIComponent(id)}`);
      S.pos = layoutFor(graph);
      fillSelects(); renderMeta(); renderTasks();
      const first = graph.tasks.find((t) => t.start !== t.goal) || graph.tasks[0];
      if (linkRequest) {
        const r = linkRequest;
        linkRequest = null;
        applyTask({ start: r.start, goal: r.goal, required: r.required, blocked: r.blocked.split(';').filter(Boolean).map((p) => p.split('>')) });
      } else if (first) applyTask(first);
      else {
        S.req = { start: '', goal: '', required: '', blocked: new Set() };
        syncRequestUI(); solveSoon(0);
      }
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  // ---------- interaction ----------
  function setSlot(slot, id) {
    if (slot === 'required' && S.req.required === id) id = '';
    S.req[slot] = id;
    syncRequestUI();
    solveSoon(0);
  }

  function onNodeClick(id, ev) {
    if (S.pick) {
      const slot = S.pick;
      setPick(null);
      setSlot(slot, id);
      return;
    }
    if (ev.shiftKey) setSlot('start', id);
    else if (ev.altKey) setSlot('required', id);
    else setSlot('goal', id);
  }

  function setPick(slot) {
    S.pick = slot;
    $$('.pick').forEach((b) => b.classList.toggle('active', b.dataset.pick === slot));
    document.body.classList.toggle('picking', !!slot);
    if (slot) toast(`Click a building to set the ${slot === 'required' ? 'required stop' : slot}.`, 'info', 2500);
  }

  function attachNodeHandlers(g, id, svgRoot, algo) {
    g.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      const inv = svgRoot.getScreenCTM().inverse();
      const toLocal = (e) => new DOMPoint(e.clientX, e.clientY).matrixTransform(inv);
      const origin = toLocal(ev), start = { ...S.pos[id] };
      let moved = false;
      const move = (e) => {
        const p = toLocal(e), dx = p.x - origin.x, dy = p.y - origin.y;
        if (!moved && Math.hypot(dx, dy) < 4) return;
        moved = true;
        S.pos[id] = { x: clamp(start.x + dx, 30, W - 30), y: clamp(start.y + dy, 40, H - 40) };
        scheduleRender();
      };
      const up = (e) => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
        window.removeEventListener('pointercancel', up);
        if (moved) store.set(`crp:pos:${S.dataset}`, S.pos);
        else onNodeClick(id, e);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
      window.addEventListener('pointercancel', up);
    });
    g.addEventListener('pointerenter', (ev) => showTooltip(ev, id, algo));
    g.addEventListener('pointermove', (ev) => moveTooltip(ev));
    g.addEventListener('pointerleave', hideTooltip);
    g.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') onNodeClick(id, ev); });
  }

  function showTooltip(ev, id, algo) {
    const tip = $('#tooltip'), run = runOf(algo);
    const rows = [];
    const outs = S.graph.edges.filter((e) => e.source === id).length;
    const ins = S.graph.edges.filter((e) => e.target === id).length;
    rows.push(['edges out / in', `${outs} / ${ins}`]);
    if (run) {
      const k = Math.min(S.step, run.trace.length);
      run.trace.slice(0, k).forEach((t, i) => {
        if (t.node !== id) return;
        const which = S.req.required ? (t.done ? 'after stop' : 'before stop') : 'state';
        rows.push([`#${i + 1} ${which}`, algo === 'astar' ? `g ${fmt(t.g)} · f ${fmt(t.f)}` : `g ${fmt(t.g)}`]);
      });
      if (algo === 'astar' && run.h && run.heuristic === 'euclidean') rows.push(['h (estimate)', fmt(run.h[id])]);
    }
    tip.innerHTML = '';
    tip.append(el('strong', {}, id));
    rows.forEach(([a, b]) => tip.append(el('div', { class: 'row' }, [el('span', {}, a), el('b', {}, b)])));
    tip.hidden = false;
    moveTooltip(ev);
  }
  function moveTooltip(ev) {
    const tip = $('#tooltip');
    if (tip.hidden) return;
    const x = Math.min(ev.clientX + 16, window.innerWidth - tip.offsetWidth - 12);
    const y = Math.min(ev.clientY + 16, window.innerHeight - tip.offsetHeight - 12);
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  }
  function hideTooltip() { const tip = $('#tooltip'); if (tip) tip.hidden = true; }

  function toggleBlocked(k) {
    if (S.req.blocked.has(k)) S.req.blocked.delete(k); else S.req.blocked.add(k);
    syncRequestUI();
    solveSoon(0);
  }

  function onEdgeClick(ev, g) {
    ev.stopPropagation();
    if (g.type !== 'two') { toggleBlocked(g.key); return; }
    const menu = $('#edgeMenu');
    menu.innerHTML = '';
    menu.append(el('div', { class: 'menu-title' }, `${g.u} ↔ ${g.v} · ${fmt(g.w)} min`));
    const option = (label, keys) => {
      const b = el('button', { type: 'button' }, label);
      b.addEventListener('click', () => {
        menu.hidden = true;
        const allClosed = keys.every((k) => S.req.blocked.has(k));
        keys.forEach((k) => (allClosed ? S.req.blocked.delete(k) : S.req.blocked.add(k)));
        syncRequestUI(); solveSoon(0);
      });
      menu.append(b);
    };
    option(`Close ${g.u} → ${g.v}`, [key(g.u, g.v)]);
    option(`Close ${g.v} → ${g.u}`, [key(g.v, g.u)]);
    option('Close both directions', g.keys);
    menu.hidden = false;
    menu.style.left = `${Math.min(ev.clientX, window.innerWidth - 210)}px`;
    menu.style.top = `${Math.min(ev.clientY, window.innerHeight - 160)}px`;
  }

  function setView(view) {
    S.view = view;
    store.set('crp:view', view);
    $$('#viewSwitch button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    positionGlider();
    S.routeShown = {};
    render();
    if (S.result) { S.step = 0; play(); }
  }

  function positionGlider() {
    const active = $(`#viewSwitch button[data-view="${S.view}"]`), glider = $('.seg-glider');
    if (!active) return;
    glider.style.width = `${active.offsetWidth}px`;
    glider.style.transform = `translateX(${active.offsetLeft - 4}px)`;
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    store.set('crp:theme', theme);
    if (S.graph) render();
  }

  // ---------- drag & drop / open folder ----------
  async function collectFiles(dt) {
    const entries = [...(dt.items || [])].map((i) => i.webkitGetAsEntry?.()).filter(Boolean);
    const files = [];
    let folder = null;
    async function walk(entry, depth) {
      if (entry.isFile) files.push(await new Promise((res, rej) => entry.file(res, rej)));
      else if (entry.isDirectory && depth < 2) {
        folder ||= entry.name;
        const reader = entry.createReader(), all = [];
        let batch;
        do { batch = await new Promise((res, rej) => reader.readEntries(res, rej)); all.push(...batch); } while (batch.length);
        for (const child of all) await walk(child, depth + 1);
      }
    }
    if (entries.length) for (const entry of entries) await walk(entry, 0);
    else files.push(...dt.files);
    return { folder, files };
  }

  async function classify(files) {
    const out = {};
    for (const f of files) {
      if (!/\.csv$/i.test(f.name)) continue;
      const text = await f.text(), name = f.name.toLowerCase();
      const header = (text.split(/\r?\n/)[0] || '').toLowerCase().split(',').map((s) => s.trim());
      let kind = name.includes('edge') ? 'edges.csv' : name.includes('node') ? 'nodes.csv' : name.includes('task') ? 'tasks.csv' : null;
      if (!kind) {
        if (header.includes('x') && header.includes('y')) kind = 'nodes.csv';
        else if (header.includes('start')) kind = 'tasks.csv';
        else if (header.includes('from') || header.includes('source')) kind = 'edges.csv';
      }
      if (kind && !out[kind]) out[kind] = text;
    }
    return out;
  }

  function setupDrop() {
    const zone = $('#dropzone');
    let depth = 0;
    const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
    window.addEventListener('dragenter', (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth++; zone.classList.add('show'); });
    window.addEventListener('dragover', (e) => { if (hasFiles(e)) e.preventDefault(); });
    window.addEventListener('dragleave', (e) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) zone.classList.remove('show'); });
    window.addEventListener('drop', async (e) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      zone.classList.remove('show');
      try {
        const { folder, files } = await collectFiles(e.dataTransfer);
        const parsed = await classify(files);
        if (!parsed['edges.csv']) throw new Error('No edges file found. Drop a folder with edges.csv, or the CSV files themselves.');
        const { id } = await call('/api/upload', { name: folder || 'dropped graph', files: parsed });
        toast(`Loaded ${Object.keys(parsed).join(', ')}`, 'info');
        await loadDatasets(id);
      } catch (err) {
        toast(err.message, 'error', 7000);
      }
    });
  }

  function setupOpenDialog() {
    const dialog = $('#openDialog');
    $('#openFolder').addEventListener('click', () => { dialog.showModal(); $('#folderPath').focus(); });
    dialog.addEventListener('close', async () => {
      if (dialog.returnValue !== 'open') return;
      const path = $('#folderPath').value.trim().replace(/^"(.*)"$/, '$1');
      if (!path) return;
      try {
        const { id } = await call('/api/open', { path });
        await loadDatasets(id);
        toast(`Opened ${path}`, 'info');
      } catch (err) {
        toast(err.message, 'error', 7000);
      }
    });
  }

  // ---------- wiring ----------
  function bind() {
    $('#dataset').addEventListener('change', (e) => selectDataset(e.target.value));
    for (const slot of ['start', 'goal', 'required']) {
      $(`#${slot}`).addEventListener('change', (e) => { S.req[slot] = e.target.value; syncRequestUI(); solveSoon(0); });
    }
    $$('.pick').forEach((b) => b.addEventListener('click', () => setPick(S.pick === b.dataset.pick ? null : b.dataset.pick)));
    $('#swap').addEventListener('click', () => { [S.req.start, S.req.goal] = [S.req.goal, S.req.start]; syncRequestUI(); solveSoon(0); });
    $('#reset').addEventListener('click', () => { S.req.required = ''; S.req.blocked.clear(); syncRequestUI(); solveSoon(0); });
    $('#clearBlocked').addEventListener('click', () => { S.req.blocked.clear(); syncRequestUI(); solveSoon(0); });
    $('#vmax').addEventListener('input', (e) => { S.vmax = Number(e.target.value); renderHeuristic(); solveSoon(220); });
    $$('#viewSwitch button').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
    $('#showH').addEventListener('change', (e) => { S.showH = e.target.checked; render(); });
    $('#showWeights').addEventListener('change', (e) => { S.showWeights = e.target.checked; render(); });
    $('#relayout').addEventListener('click', () => {
      if (!S.graph) return;
      store.del(`crp:pos:${S.dataset}`);
      S.pos = layoutFor(S.graph, true);
      render();
    });
    $('#theme').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
    $('#play').addEventListener('click', () => (S.playing ? pause() : play()));
    $('#skip').addEventListener('click', () => seek(maxSteps()));
    $('#scrub').addEventListener('input', (e) => seek(Number(e.target.value)));
    $$('.speed button').forEach((b) => b.addEventListener('click', () => {
      S.speed = Number(b.dataset.speed);
      $$('.speed button').forEach((x) => x.classList.toggle('active', x === b));
    }));
    document.addEventListener('click', (e) => { if (!e.target.closest('#edgeMenu')) $('#edgeMenu').hidden = true; });
    document.addEventListener('keydown', (e) => {
      if (e.target.closest('input, select, textarea, dialog')) return;
      if (e.key === ' ') { e.preventDefault(); S.playing ? pause() : play(); }
      else if (e.key === 'ArrowRight') seek(S.step + 1);
      else if (e.key === 'ArrowLeft') seek(S.step - 1);
      else if (e.key === 'Home') seek(0);
      else if (e.key === 'End') seek(maxSteps());
      else if (e.key === 'Escape') { setPick(null); $('#edgeMenu').hidden = true; }
      else if (e.key === '1') setView('astar');
      else if (e.key === '2') setView('ucs');
      else if (e.key === '3') setView('race');
    });
    window.addEventListener('resize', positionGlider);
    setupDrop();
    setupOpenDialog();
  }

  /* Deep links for demos: ?view=race&start=Gate&goal=Workshop&required=Canteen&blocked=A>B;C>D&theme=light */
  const params = new URLSearchParams(location.search);
  let linkRequest = params.has('start') || params.has('goal')
    ? { start: params.get('start') || '', goal: params.get('goal') || '', required: params.get('required') || '', blocked: params.get('blocked') || '' }
    : null;

  async function init() {
    if (['astar', 'ucs', 'race'].includes(params.get('view'))) S.view = params.get('view');
    if (params.has('vmax')) { S.vmax = clamp(Number(params.get('vmax')) || 80, 20, 200); $('#vmax').value = S.vmax; }
    const theme = ['light', 'dark'].includes(params.get('theme')) ? params.get('theme')
      : store.get('crp:theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.dataset.theme = theme;
    bind();
    setView(S.view);
    renderHeuristic();
    renderResults();
    try {
      await loadDatasets();
    } catch (err) {
      toast(`Cannot reach the planner server: ${err.message}`, 'error', 10000);
    }
  }

  init();
})();
