// proven.provably.fast: renders data/board.json (written by `python3 -m proven.board`).
(() => {
  "use strict";

  const TASKS = [
    { id: "blake2s-chain-v0", title: "Hash chain", size: "n = 16,384",
      what: "Hashing a random 32-byte seed n times with BLAKE2s-256 gives y." },
    { id: "u32-matmul-v0", title: "Matrix product", size: "k = 48",
      what: "C = A x B mod 2^32 for two random k x k matrices of 32-bit words." },
    { id: "stwo-verify-v0", title: "Recursion step", size: "inner n = 1,024",
      what: "A fixed Stwo verifier accepts a given proof, whose seed stays secret." },
  ];
  const $ = (id) => document.getElementById(id);

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

  const seconds = (s) => (s === null || s === undefined ? "–" : `${s < 1 ? s.toFixed(2) : s.toFixed(1)} s`);
  const gb = (b) => (b ? `${(b / 1e9).toFixed(1)} GB` : "–");
  const kb = (b) => (b ? `${Math.round(b / 1e3).toLocaleString("en-US")} KB` : "–");
  const bits = (row) => (row.proven_bits !== null && row.proven_bits !== undefined
    ? `${row.proven_bits.toFixed(1)} proven` : (row.claimed_bits ? `${row.claimed_bits.toFixed(1)} claimed` : "–"));
  const day = (iso) => (iso ? iso.slice(0, 10) : "");

  function badge(status) {
    const tone = status.startsWith("reviewed") ? "ok" : status.startsWith("claimed") ? "dim"
      : status.startsWith("waiting") ? "wait" : "warn";
    const short = status.startsWith("failed the judge: its sheet") ? "sheet below the floor" : status;
    return el("span", { class: `badge ${tone}`, title: status }, short);
  }

  function taskCard(task, board) {
    const frontier = board.frontiers[task.id];
    const rows = board.contributions[task.id] || [];
    const reference = rows.find((row) => row.team === "stwo-circuits-reference");
    const waiting = (board.waiting || []).filter((row) => row.statement === task.id);
    const card = el("article", { class: "card" },
      el("div", {}, el("h3", { class: "card-title" }, task.title), el("p", { class: "card-sub" }, task.what)),
      el("code", {}, `${task.id}, ${task.size}`));
    const shown = frontier || reference;
    if (shown) {
      card.append(el("dl", { class: "facts" },
        el("div", {}, el("dt", {}, "prove"), el("dd", {}, seconds(frontier ? frontier.prove_seconds : shown.prove_seconds))),
        el("div", {}, el("dt", {}, "peak memory"), el("dd", {}, gb(frontier ? frontier.peak_bytes : shown.peak_bytes))),
        el("div", {}, el("dt", {}, "proof"), el("dd", {}, kb(frontier ? frontier.proof_bytes : shown.proof_bytes))),
        el("div", {}, el("dt", {}, "verify"), el("dd", {}, seconds(frontier ? frontier.verify_seconds : shown.verify_seconds)))));
    }
    const foot = frontier
      ? `Frontier: ${frontier.entry} (${frontier.team}), ${bits(frontier)} bits, since ${day(frontier.moved_at)}.`
      : `Frontier open: the next entry to pass on the host sets it.${shown ? " Above: the Stwo reference, measured on the host, whose sheet now reads " + bits(shown) + " bits." : ""}`
        + (waiting.length ? ` Waiting for the host: ${waiting.map((row) => row.entry).join(", ")}.` : "");
    const conjectured = board.conjectured && board.conjectured[task.id];
    if (conjectured) {
      card.append(el("p", { class: "card-sub" },
        `At today's conjectured settings (${conjectured.settings.n_queries} queries): ${seconds(conjectured.prove_seconds)} to prove, `
        + `${kb(conjectured.proof_bytes)}, ${seconds(conjectured.verify_seconds)} to verify.`));
    }
    card.append(el("p", { class: "card-foot" }, foot));
    return card;
  }

  function boardTable(task, board) {
    const rows = (board.contributions[task.id] || []).slice();
    for (const row of board.waiting || []) {
      if (row.statement === task.id) rows.push({ ...row, status: "waiting for its first host run" });
    }
    const section = el("section", { class: "board-task" },
      el("div", { class: "board-head" }, el("h3", {}, task.title), el("span", {}, `${task.id}, ${task.size}`)));
    if (!rows.length) {
      section.append(el("p", { class: "loading" }, "No entries yet."));
      return section;
    }
    const body = el("tbody", {}, rows.map((row) => el("tr", {},
      el("td", {}, el("span", { class: "who" }, row.entry), el("span", { class: "why" }, row.system || row.team || "")),
      el("td", {}, badge(row.status)),
      el("td", { class: "n" }, seconds(row.prove_seconds)),
      el("td", { class: "n" }, gb(row.peak_bytes)),
      el("td", { class: "n" }, kb(row.proof_bytes)),
      el("td", { class: "n" }, seconds(row.verify_seconds)),
      el("td", { class: `n bits ${row.proven_bits ? "" : "claimed"}` }, bits(row)),
      el("td", { class: "n" }, day(row.date)))));
    section.append(el("div", { class: "lb-scroll" }, el("table", { class: "lb-table" },
      el("thead", {}, el("tr", {}, ["Entry", "Status"].map((h) => el("th", {}, h)),
        ["Prove", "Memory", "Proof", "Verify", "Bits", "Judged"].map((h) => el("th", { class: "n" }, h)))),
      body)));
    return section;
  }

  function history(board) {
    const items = [];
    for (const task of TASKS) {
      for (const move of board.history[task.id] || []) items.push({ task, move });
    }
    items.sort((a, b) => (b.move.moved_at || "").localeCompare(a.move.moved_at || ""));
    return items.map(({ task, move }) => el("li", {},
      el("time", { datetime: move.moved_at || "" }, day(move.moved_at)),
      el("span", {}, move.entry
        ? `${task.title}: ${move.entry} sets the frontier at ${seconds(move.prove_seconds)}. ${move.note || ""}`
        : `${task.title}: frontier open. ${move.note || ""}`)));
  }

  async function main() {
    initTheme();
    let board;
    try {
      const response = await fetch("data/board.json", { cache: "no-cache" });
      board = await response.json();
    } catch {
      for (const id of ["task-cards", "board-tables"]) $(id).replaceChildren(el("p", { class: "loading" }, "The board could not be read."));
      return;
    }
    $("task-cards").replaceChildren(...TASKS.map((task) => taskCard(task, board)));
    $("board-tables").replaceChildren(...TASKS.map((task) => boardTable(task, board)));
    const moves = history(board);
    $("history").replaceChildren(...(moves.length ? moves : [el("li", { class: "loading" }, "No moves yet.")]));
  }

  main();
})();
