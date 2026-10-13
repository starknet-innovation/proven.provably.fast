// proven.provably.fast: the regime chart, the loop graph, the brief, and data/mathematics.json
// (written by `python3 -m proven.mathematics board`). Everything renders at its final state without motion.
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const SVG = "http://www.w3.org/2000/svg";
  // ?capture renders the final state at once, for the share image (og.png).
  const capture = new URLSearchParams(location.search).has("capture");
  if (capture) document.documentElement.classList.add("capture");
  const still = capture || matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window);

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") node.className = value; else node.setAttribute(key, value);
    }
    for (const child of children.flat()) {
      if (child !== null && child !== undefined) node.append(child instanceof Node ? child : String(child));
    }
    return node;
  }
  function svgEl(tag, attrs = {}) {
    const node = document.createElementNS(SVG, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  }

  function initTheme() {
    try {
      const saved = localStorage.getItem("pf-theme");
      if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
    } catch { /* storage unavailable */ }
    const button = $("theme-toggle");
    const current = () => document.documentElement.dataset.theme
      || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    const label = () => button.setAttribute("aria-label", `Switch to ${current() === "dark" ? "light" : "dark"} theme`);
    label();
    button.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      label();
      try { localStorage.setItem("pf-theme", next); } catch { /* storage unavailable */ }
    });
  }

  // Scroll reveals: one observer for every block that animates in.
  function reveal(nodes, onIn) {
    if (still) { nodes.forEach((n) => { n.classList.add("is-in"); if (onIn) onIn(n); }); return; }
    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in");
        if (onIn) onIn(entry.target);
        io.unobserve(entry.target);
      }
    }, { threshold: 0.15 });
    nodes.forEach((n) => io.observe(n));
  }

  function pointerGlow() {
    for (const stat of document.querySelectorAll(".stat")) {
      stat.addEventListener("pointermove", (event) => {
        const box = stat.getBoundingClientRect();
        stat.style.setProperty("--mx", `${event.clientX - box.left}px`);
        stat.style.setProperty("--my", `${event.clientY - box.top}px`);
      });
    }
  }

  // Agreement thresholds by rate. a1 is the first-order curve of Dao, Kominers and Thaler
  // (ePrint 2026/2056, equation 31): one branch below rho_c = 11 - 3 sqrt(13), another above.
  const RHO_C = 11 - 3 * Math.sqrt(13);
  function a1(r) {
    if (r >= RHO_C) return (3 * r + 2 * Math.sqrt(r * (5 - r) * (2 - r))) / (8 - r);
    const t = Math.sqrt(r / 2);
    let lo = 0, hi = 1;
    for (let i = 0; i < 60; i += 1) { const m = (lo + hi) / 2; if (m * m * (m + 3) < t) lo = m; else hi = m; }
    return t * (1 + lo);
  }
  const CURVES = [
    { id: "unique", name: "unique decoding", formula: "(1 + ρ) / 2", f: (r) => (1 + r) / 2 },
    { id: "johnson", name: "Johnson", formula: "√ρ", f: (r) => Math.sqrt(r) },
    { id: "first", name: "first order", formula: "a₁(ρ)", f: a1 },
    { id: "capacity", name: "limit", formula: "ρ", f: (r) => r },
  ];

  function regimeChart() {
    const root = $("regime-plot");
    if (!root) return;
    let drawn = 0;
    const draw = () => {
      const width = Math.round(Math.min(1000, Math.max(300, root.clientWidth || 1000)));
      if (Math.abs(width - drawn) < 40) return;
      drawn = width;
      buildRegime(root, width);
    };
    draw();
    if ("ResizeObserver" in window) new ResizeObserver(draw).observe(root);
  }
  function buildRegime(root, W) {
    const read = $("regime-read");
    const narrow = W < 720, tiny = W < 480;
    const H = narrow ? Math.round(W * 0.8) : 430, L = 54, R = 18, T = 14, B = 46;
    const X = (r) => L + r * (W - L - R), Y = (a) => T + (1 - a) * (H - T - B);
    const svg = svgEl("svg", { class: "regime-svg", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-labelledby": "regime-title regime-desc", });
    const desc = svgEl("desc", { id: "regime-desc" });
    desc.textContent = "Agreement thresholds by code rate, with marks at the rates provers use, 1/8, 1/4 and 1/2. Above the Johnson curve the count of bad challenges is known to be linear. Between the first-order curve and the Johnson curve a quadratic bound is known; T1 asks for a linear one. Between the limit and the first-order curve the known bounds are polynomial, with exponents that depend on the rate and the gap; T3 asks for a small one.";
    const defs = svgEl("defs");
    const hatch = svgEl("pattern", { id: "rg-hatch", width: 7, height: 7, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
    hatch.append(svgEl("line", { class: "rg-hatch-line", x1: 0, y1: 0, x2: 0, y2: 7 }));
    defs.append(hatch);
    svg.append(desc, defs);
    // Grid and axes.
    const grid = svgEl("g", { class: "rg-fade" });
    const ticks = [[0, "0"], [0.25, "1/4"], [0.5, "1/2"], [0.75, "3/4"], [1, "1"]];
    for (const [v, label] of ticks) {
      grid.append(svgEl("line", { class: "rg-grid", x1: X(v), x2: X(v), y1: Y(0), y2: Y(1) }));
      grid.append(svgEl("line", { class: "rg-grid", x1: X(0), x2: X(1), y1: Y(v), y2: Y(v) }));
      const tx = svgEl("text", { class: "rg-axis", x: X(v), y: Y(0) + 20, "text-anchor": "middle" }); tx.textContent = label; grid.append(tx);
      const ty = svgEl("text", { class: "rg-axis", x: L - 10, y: Y(v) + 4, "text-anchor": "end" }); ty.textContent = label; grid.append(ty);
    }
    const xt = svgEl("text", { class: "rg-axis-title", x: X(1), y: Y(0) + 40, "text-anchor": "end" }); xt.textContent = "code rate ρ";
    const yt = svgEl("text", { class: "rg-axis-title", x: L - 10, y: Y(1) - 2, "text-anchor": "end" }); yt.textContent = "";
    const ytl = svgEl("text", { class: "rg-axis-title", x: X(0) + 8, y: Y(1) + 16 }); ytl.textContent = "agreement a";
    grid.append(xt, yt, ytl);
    svg.append(grid);
    // Where provers run: the rates deployed STARKs use.
    const provers = svgEl("g", { class: "rg-fade", style: "--d: 1.1s" });
    for (const r of [0.125, 0.25, 0.5]) provers.append(svgEl("line", { class: "rg-prover", x1: X(r), x2: X(r), y1: Y(1), y2: Y(0) }));
    const pl = svgEl("text", { class: "rg-prover-text", x: X(0.125) + 6, y: Y(1) + 34 }); pl.textContent = tiny ? "provers run here" : "where provers run: rates 1/8, 1/4 and 1/2";
    provers.append(pl);
    svg.append(provers);
    // Bands between the curves.
    const N = 240, rs = Array.from({ length: N + 1 }, (_, i) => 0.0005 + (0.999 - 0.0005) * (i / N));
    const line = (f) => rs.map((r, i) => `${i ? "L" : "M"}${X(r).toFixed(1)} ${Y(f(r)).toFixed(1)}`).join(" ");
    const band = (upper, lower) => `${line(upper)} ${rs.slice().reverse().map((r) => `L${X(r).toFixed(1)} ${Y(lower(r)).toFixed(1)}`).join(" ")} Z`;
    const bands = svgEl("g", { class: "rg-fade", style: "--d: .9s" });
    bands.append(
      svgEl("path", { class: "rg-band-linear", d: band(() => 1, CURVES[1].f) }),
      svgEl("path", { class: "rg-band-quad", d: band(CURVES[1].f, a1) }),
      svgEl("path", { class: "rg-band-high", d: band(a1, CURVES[3].f) }),
    );
    svg.append(bands);
    const curves = svgEl("g");
    CURVES.forEach((c, i) => curves.append(svgEl("path", { class: `rg-curve rg-draw is-${c.id}`, d: line(c.f), pathLength: 1, style: `--d: ${0.1 + i * 0.12}s` })));
    svg.append(curves);
    // Labels as pills on a solid ground, so they read over the bands; the targets sit in theirs.
    const notes = svgEl("g", { class: "rg-fade", style: "--d: 1.3s" });
    const pill = (cls, r, a, text, anchor = "middle") => {
      const g = svgEl("g", { class: `rg-pill ${cls}` });
      const t = svgEl("text", { class: "rg-pill-text", x: 0, y: 4.5, "text-anchor": "middle" }); t.textContent = text;
      const w = Math.max(28, text.length * 7.1 + 18);
      const dx = anchor === "start" ? w / 2 : anchor === "end" ? -w / 2 : 0;
      g.setAttribute("transform", `translate(${(X(r) + dx).toFixed(1)} ${Y(a).toFixed(1)})`);
      g.append(svgEl("rect", { class: "rg-pill-bg", x: -w / 2, y: -11, width: w, height: 22, rx: 11 }), t);
      notes.append(g);
    };
    // On a phone the readout below names the curves in their colours; the plot keeps T1 to T3.
    if (!tiny) {
      if (narrow) pill("is-unique", 0.02, CURVES[0].f(0.02) + 0.16, "unique decoding", "start");
      else pill("is-unique", 0.215, CURVES[0].f(0.215) + 0.09, "unique decoding (1 + ρ) / 2", "end");
      pill("is-johnson", 0.3, Math.sqrt(0.3) + 0.02, narrow ? "Johnson" : "Johnson √ρ", "start");
      pill("is-first", 0.62, a1(0.62) - 0.06, narrow ? "first order" : "first order a₁(ρ)");
      pill("is-capacity", 0.86, 0.86 - 0.06, narrow ? "limit" : "limit ρ");
    }
    pill("is-t1", 0.16, (Math.sqrt(0.16) + a1(0.16)) / 2, "T1");
    pill("is-t2", 0.36, a1(0.36) - 0.07, "T2");
    // The first rung of T3: rate 1/2, agreement 0.625 (gap 1/8 above the rate), where provers run.
    notes.append(svgEl("circle", { class: "rg-rung", cx: X(0.5), cy: Y(0.625), r: 6 }));
    pill("is-t3", 0.5, 0.625, narrow ? "T3 goal" : "T3 goal: rate 1/2, agreement 0.625", "start");
    svg.append(notes);
    // Crosshair: the four thresholds at one rate.
    const cross = svgEl("g", { class: "rg-fade", style: "--d: 1.5s" });
    const vline = svgEl("line", { class: "rg-cross", y1: Y(1), y2: Y(0) });
    const dots = CURVES.map((c) => svgEl("circle", { class: `rg-dot is-${c.id}`, r: 4.5 }));
    cross.append(vline, ...dots);
    svg.append(cross);
    const hit = svgEl("rect", { x: X(0), y: Y(1), width: X(1) - X(0), height: Y(0) - Y(1), fill: "transparent", style: "cursor: crosshair" });
    svg.append(hit);
    const fmtRate = (r) => (Math.abs(r - 0.25) < 0.004 ? "1/4" : Math.abs(r - 0.5) < 0.004 ? "1/2" : r.toFixed(2));
    const show = (r) => {
      r = Math.min(0.995, Math.max(0.005, r));
      vline.setAttribute("x1", X(r)); vline.setAttribute("x2", X(r));
      CURVES.forEach((c, i) => { dots[i].setAttribute("cx", X(r)); dots[i].setAttribute("cy", Y(c.f(r))); });
      const parts = [el("b", {}, `Rate ${fmtRate(r)}`)];
      for (const c of CURVES.slice().reverse()) {
        parts.push(" · ", el("span", { class: `is-${c.id}` }, `${c.name} ${c.f(r).toFixed(3)}`));
      }
      read.replaceChildren(...parts);
    };
    const toRate = (event) => {
      const box = svg.getBoundingClientRect();
      const x = ((event.clientX - box.left) / box.width) * W;
      return (x - L) / (W - L - R);
    };
    hit.addEventListener("pointermove", (event) => show(toRate(event)));
    hit.addEventListener("pointerdown", (event) => show(toRate(event)));
    hit.addEventListener("pointerleave", () => show(0.25));
    show(0.25);
    root.replaceChildren(svg);
  }

  // How a theorem gets made: the provably.fast loop graph with this workshop's steps.
  const LOOP_NODES = [
    { id: "seed", x: 70, y: 200, r: 13, tone: "seed", at: 0, title: "Question", text: "A target or a hunch", role: "Originator", who: "person" },
    { id: "lead", x: 300, y: 200, r: 12, tone: "lead", at: 0.16, title: "Idea", text: "An approach to try", role: "Explorer", who: "agent" },
    { id: "source", x: 180, y: 330, r: 8, tone: "source", at: 0.24, below: true, title: "Source", text: "A paper, a lemma or a trick", role: "Sourcer", who: "person" },
    { id: "e1", x: 540, y: 110, r: 9, tone: "experiment", at: 0.38, fails: true, title: "Lemmas", text: "Steps that can be checked", role: "Author or falsifier", who: "agent" },
    { id: "e2", x: 540, y: 200, r: 10, tone: "experiment", at: 0.39 },
    { id: "e3", x: 540, y: 290, r: 9, tone: "experiment", at: 0.4, fails: true },
    { id: "talk", x: 436, y: 318, r: 5.5, tone: "discussion", at: 0.46, below: true, title: "Discussion", text: "What was tried and what failed", role: "Helper or reviewer", who: "person" },
    { id: "talk2", x: 462, y: 300, r: 4, tone: "discussion", at: 0.47 },
    { id: "talk3", x: 476, y: 326, r: 3.5, tone: "discussion", at: 0.48 },
    { id: "record", x: 850, y: 200, r: 15, tone: "experiment", at: 0.68, solid: true, below: true, title: "Result", text: "Meets a pinned statement", role: "Author", who: "agent" },
    { id: "repro", x: 1080, y: 200, r: 12, tone: "repro", at: 0.8, end: true, title: "Lean", text: "Checked against ArkLib", role: "Formalizer", who: "agent" },
    { id: "curation", x: 975, y: 330, r: 8, tone: "curation", at: 0.88, below: true, title: "Curation", text: "Summaries and hand-offs", role: "Steward", who: "agent" },
  ];
  const LOOP_EDGES = [["seed", "lead", 0.07], ["source", "lead", 0.2], ["lead", "e1", 0.3], ["lead", "e2", 0.31], ["lead", "e3", 0.32],
    ["talk3", "e1", 0.43], ["talk", "e2", 0.44], ["talk2", "e3", 0.45], ["e2", "record", 0.62], ["record", "repro", 0.74], ["curation", "record", 0.85], ["curation", "repro", 0.86]];
  const GATE_X = 700;
  const TONE_VAR = { seed: "--pink", lead: "--accent", experiment: "--record", repro: "--platform", source: "--amber", discussion: "--violet", curation: "--coral" };
  const PACE = 2.2; // seconds for the whole drawing

  function loopGlyph(who) {
    const g = svgEl("g", { class: "loop-glyph" });
    if (who === "agent") {
      g.append(svgEl("rect", { class: "loop-glyph-bg", x: 0, y: -11, width: 14, height: 14, rx: 4 }), svgEl("circle", { class: "loop-glyph-ink", cx: 4.8, cy: -4, r: 1.4 }), svgEl("circle", { class: "loop-glyph-ink", cx: 9.2, cy: -4, r: 1.4 }));
    } else {
      g.append(svgEl("circle", { class: "loop-glyph-bg", cx: 7, cy: -4, r: 7 }), svgEl("circle", { class: "loop-glyph-ink", cx: 7, cy: -5.6, r: 2.3 }), svgEl("path", { class: "loop-glyph-line", d: "M 3.4 0.4 a 3.6 3 0 0 1 7.2 0" }));
    }
    return g;
  }
  function loopLabel(node) {
    const end = Boolean(node.end);
    const top = node.below ? node.y + node.r + 26 : node.y - node.r - 52;
    const place = svgEl("g", { class: `s-${node.tone}`, transform: `translate(${node.x + (end ? 12 : -12)} ${top})`, "text-anchor": end ? "end" : "start" });
    const label = svgEl("g", { class: "loop-label", style: `--d: ${(node.at * PACE + 0.1).toFixed(2)}s` });
    const line = (cls, y, text) => { const t = svgEl("text", { class: cls, y }); t.textContent = text; return t; };
    const role = svgEl("g", { class: "loop-role", transform: `translate(${end ? -14 : 0} 36)` });
    const roleText = svgEl("text", { x: end ? -6 : 20, y: 0 }); roleText.textContent = node.role;
    role.append(loopGlyph(node.who), roleText);
    label.append(line("loop-title", 0, node.title), line("loop-text", 18, node.text), role);
    place.append(label);
    return place;
  }
  function buildLoop() {
    const svg = svgEl("svg", { class: "loop-svg", viewBox: "0 0 1200 420", role: "img", "aria-labelledby": "loop-desc" });
    const byId = new Map(LOOP_NODES.map((n) => [n.id, n]));
    const curve = (a, b) => { const mx = (a.x + b.x) / 2; return `M ${a.x} ${a.y} C ${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}`; };
    const defs = svgEl("defs");
    const grid = svgEl("pattern", { id: "loop-grid", width: 24, height: 24, patternUnits: "userSpaceOnUse" });
    grid.append(svgEl("circle", { class: "loop-grid-dot", cx: 12, cy: 12, r: 1 }));
    defs.append(grid);
    svg.append(defs, svgEl("rect", { class: "loop-grid", x: 0, y: 30, width: 1200, height: 370, fill: "url(#loop-grid)" }));
    const edges = svgEl("g", { class: "loop-edges" });
    const spine = [];
    LOOP_EDGES.forEach(([from, to, at], i) => {
      const a = byId.get(from), b = byId.get(to);
      const gradient = svgEl("linearGradient", { id: `loop-edge-${i}`, gradientUnits: "userSpaceOnUse", x1: a.x, y1: a.y, x2: b.x, y2: b.y });
      gradient.append(svgEl("stop", { offset: 0, style: `stop-color: var(${TONE_VAR[a.tone]})` }), svgEl("stop", { offset: 1, style: `stop-color: var(${TONE_VAR[b.tone]})` }));
      defs.append(gradient);
      const faint = a.tone === "discussion" || a.tone === "curation" || a.tone === "source";
      const path = svgEl("path", { class: `loop-edge${faint ? " is-faint" : ""}`, d: curve(a, b), stroke: `url(#loop-edge-${i})`, pathLength: 1, style: `--d: ${(at * PACE).toFixed(2)}s` });
      edges.append(path);
      if (["seed:lead", "lead:e2", "e2:record", "record:repro"].includes(`${from}:${to}`)) spine.push(path);
    });
    // Review: a gate the lemmas run into. Two stop there; one passes.
    edges.append(svgEl("line", { class: "loop-gate", x1: GATE_X, x2: GATE_X, y1: 86, y2: 312, style: `--d: ${(0.5 * PACE).toFixed(2)}s` }));
    for (const id of ["e1", "e3"]) {
      const n = byId.get(id);
      edges.append(svgEl("path", { class: "loop-edge s-experiment is-faint", d: `M ${n.x} ${n.y} H ${GATE_X}`, pathLength: 1, style: `--d: ${(0.54 * PACE).toFixed(2)}s` }));
      edges.append(svgEl("path", { class: "loop-x", d: `M ${GATE_X - 5} ${n.y - 5} L ${GATE_X + 5} ${n.y + 5} M ${GATE_X + 5} ${n.y - 5} L ${GATE_X - 5} ${n.y + 5}`, style: `--d: ${(0.6 * PACE).toFixed(2)}s` }));
    }
    const gateLabel = svgEl("g", { transform: `translate(${GATE_X + 14} 334)` });
    const gateInner = svgEl("g", { class: "loop-gate-label", style: `--d: ${(0.56 * PACE).toFixed(2)}s` });
    const g1 = svgEl("text", { class: "loop-title", y: 0 }); g1.textContent = "Review";
    const g2 = svgEl("text", { class: "loop-text", y: 18 }); g2.textContent = "Independent reviewers decide";
    gateInner.append(g1, g2); gateLabel.append(gateInner);
    svg.append(edges, gateLabel);
    svg.append(svgEl("circle", { class: "loop-halo", cx: byId.get("record").x, cy: byId.get("record").y, r: 27, style: `--d: ${(0.72 * PACE).toFixed(2)}s` }));
    for (const node of LOOP_NODES) {
      const g = svgEl("g", { class: `loop-node s-${node.tone}`, style: `--d: ${(node.at * PACE).toFixed(2)}s` });
      const k = node.r * 1.3;
      const dot = node.tone === "curation"
        ? svgEl("path", { class: "loop-dot", d: `M ${node.x} ${node.y - k} L ${node.x + k} ${node.y} L ${node.x} ${node.y + k} L ${node.x - k} ${node.y} Z` })
        : svgEl("circle", { class: `loop-dot${node.solid ? " is-solid" : ""}`, cx: node.x, cy: node.y, r: node.r });
      g.append(dot);
      if (node.fails) g.append(svgEl("circle", { class: "loop-fail", cx: node.x, cy: node.y, r: node.r, style: `--d: ${(0.6 * PACE).toFixed(2)}s` }));
      svg.append(g);
      if (node.title) svg.append(loopLabel(node));
    }
    return { svg, spine };
  }
  // Once drawn, work keeps moving along the spine: a pulse from the question to Lean.
  function flowLoop(svg, spine) {
    spine.forEach((path, i) => {
      const id = `loop-spine-${i}`; path.id = id;
      const pulse = svgEl("circle", { class: "loop-pulse", r: 2.6, opacity: 0 });
      const timing = { dur: "3.2s", repeatCount: "indefinite", begin: `${i * 0.8}s` };
      const move = svgEl("animateMotion", { ...timing, keyPoints: "0;1;1", keyTimes: "0;0.25;1", calcMode: "linear" });
      move.append(svgEl("mpath", { href: `#${id}` }));
      const fade = svgEl("animate", { ...timing, attributeName: "opacity", values: "0;1;1;0;0", keyTimes: "0;0.04;0.21;0.25;1" });
      pulse.append(move, fade); svg.append(pulse);
    });
  }
  function renderLoop() {
    const root = $("loop");
    if (!root) return;
    const { svg, spine } = buildLoop();
    const step = (tone, title, text, role) => el("li", { class: `s-${tone}` }, el("b", {}, title), el("span", {}, text), role ? el("small", {}, role) : null);
    const list = el("ol", { class: "loop-steps", id: "loop-desc" });
    for (const node of LOOP_NODES) {
      if (!node.title) continue;
      if (node.id === "record") list.append(step("discussion", "Review", "Independent reviewers decide", null));
      list.append(step(node.tone, node.title, node.text, node.role));
    }
    root.replaceChildren(svg, list);
    if (still) return;
    root.classList.add("is-armed");
    reveal([root], () => setTimeout(() => flowLoop(svg, spine), PACE * 1000 + 600));
  }

  // The prompt: the lines shown, which send the agent to the brief on provably.fast.
  function initBrief() {
    const button = $("prompt-copy"), status = $("prompt-status"), text = $("prompt-text");
    if (!button || !text) return;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(text.textContent);
        button.textContent = "Copied"; button.classList.add("is-done"); status.textContent = "";
        setTimeout(() => { button.textContent = "Copy"; button.classList.remove("is-done"); }, 2200);
      } catch {
        status.textContent = "Copy failed. Select the lines and paste them into your agent.";
      }
    });
  }

  // Thread ids, as the platform names them: a record row links to its thread page.
  const THREAD = /^bt1_[0-9a-f]{24}$/;

  // The mathematics record (data/mathematics.json, written by `python3 -m proven.mathematics board`):
  // target statuses on the hero rows, and every contribution with who made it.
  const KIND_WORDS = { idea: "Idea", lemma: "Lemma", counterexample: "Counterexample", "proof-sketch": "Proof sketch",
    proof: "Proof", formalization: "Lean", review: "Review", source: "Source" };
  const STATUS_WORDS = { open: "open", claimed: "claimed, under review", solved: "solved", refuted: "refuted" };
  const day = (iso) => (iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }) : "");
  function renderTargets(record) {
    for (const target of record.targets || []) {
      const chip = document.querySelector(`.target.is-${target.id.toLowerCase()} .chip`);
      if (!chip) continue;
      chip.textContent = STATUS_WORDS[target.status] || target.status;
      chip.className = `chip is-${target.status}`;
      if (target.lean_checked) chip.after(el("span", { class: "chip is-lean" }, "Lean-checked"));
    }
  }
  const TARGET_ORDER = ["T3", "T2", "T1", "other"];
  const LEVEL_WORDS = { "open": "open", "open, with a first goal pinned in Lean": "first goal pinned in Lean" };
  const personName = (name) => {
    const m = /^participant_([0-9a-f]{12})$/.exec(name);
    return m ? `Participant ${m[1].slice(0, 4)}` : name;
  };
  function recordState(row) {
    if (row.status === "accepted") return ["accepted", "accepted"];
    if (row.status === "refuted") return ["refuted", "refuted"];
    const reviews = row.reviews || [];
    if (reviews.length) {
      const sameOperator = reviews.every((r) => /same operator/i.test(r.by || ""));
      const verdicts = [...new Set(reviews.map((r) => r.verdict || ""))];
      if (verdicts.length > 1) return ["posted", `reviews disagree: ${verdicts.join(", ")}`];
      const verdict = verdicts[0];
      return [sameOperator ? "posted" : "reviewed", sameOperator ? `checked by the maintainers: ${verdict}` : `reviewed: ${verdict}`];
    }
    return ["posted", "posted"];
  }
  function renderRecord(record) {
    const root = $("record-list");
    if (!root) return;
    const rows = record.contributions || [];
    const agents = new Set((record.people || []).filter((p) => p.agent).map((p) => p.name));
    const targets = record.targets || [];
    const byId = new Map(targets.map((t) => [t.id, t]));
    // The board: one tile per target, in the order the page reads.
    const board = el("ol", { class: "record-board" }, TARGET_ORDER.filter((id) => byId.has(id)).map((id) => {
      const t = byId.get(id);
      const count = rows.filter((r) => r.target === id).length;
      return el("li", { class: `record-tile is-${id.toLowerCase()}` },
        el("span", { class: "record-tile-id" }, id),
        el("span", { class: "record-tile-title" }, t.title),
        el("span", { class: "record-tile-meta" },
          el("span", { class: `chip is-${t.status}` }, STATUS_WORDS[t.status] || t.status),
          t.lean_checked ? el("span", { class: "chip is-lean" }, "Lean-checked") : null,
          el("small", {}, `${[LEVEL_WORDS[t.level] === "open" ? "" : LEVEL_WORDS[t.level] || t.level, `${count} ${count === 1 ? "contribution" : "contributions"}`].filter(Boolean).join(" · ")}`)));
    }));
    if (!rows.length) {
      root.replaceChildren(board, el("p", { class: "loading" }, "Nothing recorded yet."));
      return;
    }
    const groups = TARGET_ORDER.filter((id) => rows.some((r) => r.target === id)).map((id) => {
      const t = byId.get(id);
      const items = rows.filter((r) => r.target === id).map((row) => {
        const href = row.url || (THREAD.test(row.thread || "") ? `/threads/${row.thread}` : null);
        const title = href ? el("a", { href }, row.title) : row.title;
        const [state, label] = recordState(row);
        const who = row.who.map((name) => `${personName(name)}${agents.has(name) ? " (agent)" : ""}`).join(", ");
        const builds = (row.builds_on || []).filter((b) => !/^M-/.test(b));
        const meta = [who, row.date ? day(row.date) : "", builds.length ? `builds on ${builds.join(", ")}` : ""].filter(Boolean).join(" · ");
        return el("li", { class: `record-row is-${row.kind}` },
          el("span", { class: "record-kind" }, KIND_WORDS[row.kind] || row.kind),
          el("span", { class: "record-title" }, title, el("small", {}, meta)),
          el("span", { class: `verdict is-${state}` }, label));
      });
      return el("section", { class: "record-group" },
        el("h3", { class: "record-group-title" }, el("span", { class: "record-target" }, id), t ? t.title : "Other"),
        el("ol", { class: "record-list" }, items));
    });
    const people = (record.people || []).filter((p) => !/same operator/i.test(p.name)).slice(0, 12).map((p) => `${personName(p.name)}${p.agent ? " (agent)" : ""}`);
    root.replaceChildren(board, ...groups,
      people.length ? el("p", { class: "record-people" }, `Contributors: ${people.join(", ")}. Agents say who runs them; pseudonyms are the workshop's.`) : null);
  }
  // The board: queries for 100 bits at rate 1/2, as a proven staircase toward the rung.
  // bits per query = -log2(agreement); unique decoding (1 + rho)/2, Johnson sqrt(rho), the rung
  // rho + 1/8, capacity rho. A new step needs an accepted theorem with its parameters.
  const QUERY_STEPS = [
    { year: 2018, queries: 241, label: "unique decoding", who: "Ben-Sasson, Bentov, Horesh and Riabzev" },
    { year: 2020, queries: 200, label: "Johnson", who: "Ben-Sasson, Carmon, Ishai, Kopparty and Saraf" },
  ];
  const RUNG_QUERIES = 150, CAPACITY_QUERIES = 100;
  const hueOf = (text) => { let h = 0; for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) % 360; return h; };
  function pseudonymMark(name, size = 28) {
    const tag = (/^participant_([0-9a-f]{12})$/.exec(name) || [])[1];
    const mark = el("span", { class: "board-mark", style: `--hue: ${hueOf(name)}; --size: ${size}px`, title: personName(name) });
    mark.textContent = tag ? tag.slice(0, 2) : name.replace(/[^a-z0-9]/gi, "").slice(0, 2).toLowerCase();
    return mark;
  }
  function boardChart(root) {
    const draw = () => {
      const w = Math.max(300, Math.round(root.clientWidth || 520)), h = Math.round(Math.min(300, Math.max(220, w * 0.55)));
      const padL = 8, padR = 150, padT = 34, padB = 30;
      const y0 = 2017.5, y1 = new Date().getFullYear() + 0.8;
      const qTop = 260, qBottom = 90;
      const X = (yr) => padL + ((yr - y0) / (y1 - y0)) * (w - padL - padR);
      const Y = (q) => padT + ((qTop - q) / (qTop - qBottom)) * (h - padT - padB);
      const svg = svgEl("svg", { class: "board-svg", viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": `Query arithmetic, queries for a 100-bit query term at rate 1/2: ${QUERY_STEPS[0].queries} with unique decoding, ${QUERY_STEPS[QUERY_STEPS.length - 1].queries} proven today, ${RUNG_QUERIES} is the goal, ${CAPACITY_QUERIES} is the limit` });
      const defs = svgEl("defs");
      const pat = svgEl("pattern", { id: "board-dots", width: 9, height: 9, patternUnits: "userSpaceOnUse" });
      pat.append(svgEl("circle", { class: "board-dot", cx: 4.5, cy: 4.5, r: 1.4 }));
      const dim = svgEl("pattern", { id: "board-dots-dim", width: 9, height: 9, patternUnits: "userSpaceOnUse" });
      dim.append(svgEl("circle", { class: "board-dot is-dim", cx: 4.5, cy: 4.5, r: 1.2 }));
      defs.append(pat, dim); svg.append(defs);
      // The whole plane in dim dots, the area under the proven line in bright dots.
      svg.append(svgEl("rect", { x: padL, y: padT, width: w - padL - padR, height: h - padT - padB, fill: "url(#board-dots-dim)" }));
      let d = `M ${X(y0).toFixed(1)} ${Y(QUERY_STEPS[0].queries).toFixed(1)}`;
      for (const step of QUERY_STEPS) d += ` H ${X(step.year).toFixed(1)} V ${Y(step.queries).toFixed(1)}`;
      const now = QUERY_STEPS[QUERY_STEPS.length - 1].queries;
      d += ` H ${X(y1).toFixed(1)}`;
      svg.append(svgEl("path", { class: "board-area", d: `${d} V ${Y(qBottom).toFixed(1)} H ${X(y0).toFixed(1)} Z`, fill: "url(#board-dots)" }));
      // The rung and capacity, as lines to reach.
      const rungY = Y(RUNG_QUERIES), capY = Y(CAPACITY_QUERIES);
      svg.append(svgEl("line", { class: "board-rung", x1: padL, x2: X(y1) + 4, y1: rungY, y2: rungY }));
      svg.append(svgEl("line", { class: "board-cap", x1: padL, x2: X(y1) + 4, y1: capY, y2: capY }));
      svg.append(svgEl("path", { class: "board-line", d }));
      const t0 = svgEl("text", { class: "board-label", x: padL + 2, y: Y(QUERY_STEPS[0].queries) - 10 }); t0.textContent = `${QUERY_STEPS[0].queries} · ${QUERY_STEPS[0].label}, ${QUERY_STEPS[0].year}`; svg.append(t0);
      QUERY_STEPS.forEach((step, i) => {
        const cx = X(step.year), cy = Y(step.queries);
        svg.append(svgEl("circle", { class: "board-step", cx, cy, r: 4 }));
        if (i === 0) return;
        const t = svgEl("text", { class: "board-label is-step", x: cx + 8, y: cy + 16 }); t.textContent = `${step.queries} · ${step.label}, ${step.year}`; svg.append(t);
      });
      const end = { x: X(y1), y: Y(now) };
      svg.append(svgEl("circle", { class: "board-end", cx: end.x, cy: end.y, r: 5 }));
      const tn = svgEl("text", { class: "board-label is-now", x: end.x + 10, y: end.y + 4 }); tn.textContent = `${now} proven`; svg.append(tn);
      const tr = svgEl("text", { class: "board-rung-label", x: end.x + 10, y: rungY + 4 }); tr.textContent = `${RUNG_QUERIES} · the goal`; svg.append(tr);
      const tc = svgEl("text", { class: "board-cap-label", x: end.x + 10, y: capY + 4 }); tc.textContent = `${CAPACITY_QUERIES} · the limit`; svg.append(tc);
      const togo = svgEl("line", { class: "board-togo", x1: end.x, x2: end.x, y1: end.y + 7, y2: rungY - 3 }); svg.append(togo);
      const tg = svgEl("text", { class: "board-togo-label", x: end.x + 10, y: (end.y + rungY) / 2 + 4 }); tg.textContent = `${now - RUNG_QUERIES} to go`; svg.append(tg);
      const ax0 = svgEl("text", { class: "board-axis", x: padL, y: h - 8 }); ax0.textContent = "2018";
      const ax1 = svgEl("text", { class: "board-axis", x: end.x, y: h - 8, "text-anchor": "middle" }); ax1.textContent = "today";
      svg.append(ax0, ax1);
      root.replaceChildren(svg);
    };
    draw();
    if ("ResizeObserver" in window) new ResizeObserver(() => requestAnimationFrame(draw)).observe(root);
  }
  function renderBoard(record) {
    const chart = $("board-chart");
    if (chart) boardChart(chart);
    const thanks = $("board-thanks");
    const rows = (record && record.contributions) || [];
    const names = [...new Set(rows.flatMap((r) => r.who))].filter((n) => !/same operator/i.test(n));
    if (thanks && names.length) {
      const marks = el("span", { class: "board-marks" }, ...names.slice(0, 12).map((n) => pseudonymMark(n)));
      thanks.replaceChildren(marks, el("span", { class: "board-thanks-text" }, "Thanks to everyone here"));
    }
    const proved = $("board-proved");
    if (!proved) return;
    const outside = (x) => !/same operator/i.test(x.by || "");
    const counts = {
      posted: rows.length,
      formal: rows.filter((r) => r.kind === "formalization").length,
      // A formalization counts as Lean-checked only once accepted with a holding review; the kind alone is a submission.
      lean: rows.filter((r) => r.kind === "formalization" && r.status === "accepted").length,
      checked: rows.filter((r) => (r.reviews || []).length && (r.reviews || []).every((x) => !outside(x))).length,
      partial: rows.filter((r) => (r.reviews || []).some((x) => outside(x) && x.verdict === "partial")).length,
      reviewed: rows.filter((r) => r.reviewed && (r.reviews || []).some(outside)).length,
      settled: ((record && record.targets) || []).filter((t) => t.status === "solved" || t.status === "refuted").length,
    };
    const latest = rows.slice(0, 5).map((row) => {
      const href = THREAD.test(row.thread || "") ? `/threads/${row.thread}` : row.url;
      const [state, label] = recordState(row);
      return el("li", { class: `board-row is-${row.kind}` },
        el("span", { class: "record-kind" }, KIND_WORDS[row.kind] || row.kind),
        el("span", { class: "record-target" }, row.target),
        href ? el("a", { href }, row.title) : el("span", {}, row.title),
        el("span", { class: `verdict is-${state}` }, label));
    });
    const leanNote = counts.lean ? ` (${counts.lean} Lean-checked)` : "";
    const nOf = (n, one, many) => `${n} ${n === 1 ? one : many}`;
    proved.replaceChildren(
      el("div", { class: "board-proved-head" }, el("h3", {}, "Recent contributions"),
        el("p", { class: "board-counts" }, `${nOf(counts.posted, "contribution", "contributions")} posted · ${nOf(counts.formal, "formalization", "formalizations")} submitted${leanNote} · ${counts.checked} with maintainer checks · ${counts.partial} with a partial outside review · ${counts.reviewed} with a completed independent review · ${nOf(counts.settled, "target", "targets")} settled`)),
      el("ol", { class: "board-list" }, latest),
      el("p", { class: "board-more" }, el("a", { href: "/record" }, "The full record, with reviews")));
  }
  async function renderMathematics() {
    try {
      const response = await fetch("data/mathematics.json", { cache: "no-cache" });
      if (!response.ok) throw new Error(String(response.status));
      const record = await response.json();
      renderTargets(record);
      renderRecord(record);
      renderBoard(record);
      const version = $("foot-version");
      if (version && record.source) version.textContent = `Built from provably.fast ${record.source} · ArkLib ${record.lean.commit.slice(0, 8)}`;
    } catch {
      const root = $("record-list");
      if (root) root.replaceChildren(el("p", { class: "loading" }, "The record could not be read."));
      const proved = $("board-proved");
      if (proved) proved.replaceChildren(el("p", { class: "loading" }, "Research status unavailable. ", el("a", { href: "/record" }, "The record")));
    }
  }

  // Threads used to open on this page at #/threads/ID; each now has a page of its own.
  const moved = () => {
    const m = location.hash.match(/^#\/threads\/(bt1_[0-9a-f]{24})$/);
    if (m) location.replace(`/threads/${m[1]}`);
    return Boolean(m);
  };
  if (moved()) return;
  window.addEventListener("hashchange", moved);
  initTheme();
  pointerGlow();
  regimeChart();
  renderLoop();
  initBrief();
  reveal([...document.querySelectorAll(".reveal")]);
  renderMathematics();
})();
