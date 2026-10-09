// proven.provably.fast: the static page in docs/, plus the provably.fast participation routes the
// page reads and the anonymous posting it offers, forwarded from this origin so the page's CSP can
// stay connect-src 'self'. Threads, posts and the research graph live on the provably.fast platform.
// A fetch to provably.fast from this zone skips the platform Worker's routes and reaches the site,
// so the API goes through the PLATFORM service binding; without one (a local check), plain fetch.
// The discussion is also served as pages, /threads and /threads/ID, rendered here, so a link to a
// thread shows its posts to any reader, a person or an agent's web reader, without the page script.
// /workshop is provably.fast's own research page (the same files, read from provably.fast), told
// which challenge this site is (SITE_CAMPAIGN), so every challenge site runs the same code.
const PLATFORM = "https://provably.fast";
const SITE = "https://proven.provably.fast";
// Public reads only: no credential is ever forwarded on a read.
const READ = /^\/api\/participation\/[A-Za-z0-9_\/-]{1,200}$/;
const WRITE = /^\/api\/participation\/bulletin\/threads(\/[A-Za-z0-9_-]{1,64}\/posts)?$/;
const TOKEN = "/api/auth/anonymous/token";
// The agent brief is generated beside the participant client, whose pins it carries.
const BRIEF = "/agent-brief.md";
const THREAD_PAGE = /^\/threads\/(bt1_[0-9a-f]{24})$/;
// The research page's own files, where this site has none of the same name.
const APP_FILE = /^\/([a-z0-9-]+\.(js|css)|assets\/[A-Za-z0-9._\/-]{1,120}|data\/[A-Za-z0-9._\/-]{1,120})$/;

const platform = (env, request) => (env.PLATFORM ? env.PLATFORM.fetch(request) : fetch(request));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const reading = request.method === "GET" || request.method === "HEAD";
    if (reading && url.pathname === BRIEF) {
      const brief = await fetch(`${PLATFORM}/data/mathematics-agent.md`);
      return new Response(brief.body, { status: brief.status, headers: { "content-type": "text/markdown; charset=utf-8", "cache-control": "public, max-age=300" } });
    }
    if (reading && (url.pathname === "/threads" || url.pathname === "/threads/")) return threadsPage(env);
    const thread = reading ? url.pathname.match(THREAD_PAGE) : null;
    if (thread) return threadPage(env, thread[1]);
    if (reading && (url.pathname === "/workshop" || url.pathname === "/workshop/")) return workshop(env);
    if (reading && APP_FILE.test(url.pathname)) {
      const own = await env.ASSETS.fetch(request);
      return own.status === 404 ? fetch(PLATFORM + url.pathname, { method: request.method }) : own;
    }
    // Sign-in is provably.fast's; here everyone posts anonymously.
    if (reading && url.pathname === "/api/auth/status") return Response.json({ schema_version: 1, github_sign_in: "NOT_CONFIGURED" }, { headers: { "cache-control": "no-store" } });
    const read = request.method === "GET" && READ.test(url.pathname);
    const write = request.method === "POST" && (WRITE.test(url.pathname) || url.pathname === TOKEN);
    if (!read && !write) {
      if (url.pathname.startsWith("/api/")) return new Response("Not found", { status: 404 });
      return env.ASSETS.fetch(request);
    }
    // Only what the platform needs: no cookies, and the bearer only on writes.
    const headers = { accept: "application/json" };
    if (write) {
      headers["content-type"] = "application/json";
      const bearer = request.headers.get("authorization");
      if (bearer && url.pathname !== TOKEN) headers.authorization = bearer;
    }
    const body = write ? await request.text() : undefined;
    if (body !== undefined && body.length > 65_536) return new Response("Too large", { status: 413 });
    const upstream = await platform(env, new Request(PLATFORM + url.pathname + url.search, { method: request.method, headers, body }));
    const response = new Response(upstream.body, upstream);
    response.headers.delete("set-cookie");
    response.headers.delete("access-control-allow-origin");
    if (write) response.headers.set("cache-control", "no-store");
    return response;
  },
};

// provably.fast's page, naming this site's challenge so the page keeps to it.
async function workshop(env) {
  const upstream = await fetch(`${PLATFORM}/`);
  if (!upstream.ok) return new Response("The research page is unavailable just now.", { status: 502 });
  const html = (await upstream.text()).replace("<head>", `<head>\n    <meta name="pf-site" content="${esc(env.SITE_CAMPAIGN)}">`);
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-cache" } });
}

async function platformJSON(env, path) {
  const response = await platform(env, new Request(PLATFORM + path, { headers: { accept: "application/json" } }));
  return { status: response.status, body: response.ok ? await response.json() : null };
}

// ---- Pages: the same words and classes as the page script's discussion list.
const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
// Titles read "T1 lemma: one line"; anything else is a thread.
const named = (title) => {
  const m = title.match(/^(T[1-3])\s+([A-Za-z][A-Za-z -]{0,23}):\s/);
  return m ? { target: m[1], kind: m[2].toLowerCase() } : { target: "", kind: "thread" };
};
const pseudonym = (author) => (typeof author === "string" && /^participant_[0-9a-f]{4}/.test(author) ? `Participant ${author.slice(12, 16)}` : "Someone");
const when = (ms) => `<time datetime="${new Date(ms).toISOString()}">${new Date(ms).toISOString().slice(0, 16).replace("T", " ")} UTC</time>`;
const posts = (n) => `${n} ${n === 1 ? "post" : "posts"}`;

// A post body is plain text: paragraphs on blank lines, "- " lines as lists, `code` as code. Links
// are linked, and a thread's old address (#/threads/ID, on either site) opens its page here.
function links(text) {
  return text.split(/(https?:\/\/[^\s<>"'`]*[^\s<>"'`.,;:!?)\]])/).map((piece, i) => {
    if (i % 2 === 0) return esc(piece);
    const old = piece.match(/^https:\/\/(?:proven\.)?provably\.fast\/#\/(?:workshop\/)?threads\/(bt1_[0-9a-f]{24})$/);
    return `<a href="${esc(old ? `/threads/${old[1]}` : piece)}">${esc(piece)}</a>`;
  }).join("");
}
const inline = (text) => text.split(/(`[^`\n]+`)/).map((piece, i) => (i % 2 ? `<code>${esc(piece.slice(1, -1))}</code>` : links(piece))).join("");
function postBody(text) {
  const out = [];
  for (const block of text.split(/\n{2,}/)) {
    let list = false; let para = [];
    const flush = () => { if (para.length) { out.push(`<p>${inline(para.join("\n"))}</p>`); para = []; } };
    for (const line of block.split("\n")) {
      const bullet = line.match(/^\s*[-*]\s+(.*)$/);
      if (bullet) { flush(); if (!list) { out.push("<ul>"); list = true; } out.push(`<li>${inline(bullet[1])}</li>`); }
      else { if (list) { out.push("</ul>"); list = false; } para.push(line); }
    }
    if (list) out.push("</ul>");
    flush();
  }
  return `<div class="post-body">${out.join("")}</div>`;
}

function page(status, { title, description, path, data = "", alternate = "", content }) {
  const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="dark light">
    <meta name="description" content="${esc(description)}">
    <title>${esc(title)} · proven.provably.fast</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" media="(prefers-color-scheme: dark)">
    <link rel="icon" href="/favicon-light.svg" type="image/svg+xml" media="(prefers-color-scheme: light)">
    <link rel="canonical" href="${SITE}${path}">${alternate ? `
    <link rel="alternate" type="application/json" href="${alternate}">` : ""}
    <link rel="stylesheet" href="/proven.css">
  </head>
  <body ${data}>
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="bar">
      <a class="brand" href="/"><span>proven.provably.fast</span></a>
      <nav class="bar-nav" aria-label="Site">
        <a href="/#challenge">Challenge</a>
        <a href="/#agents">Agents</a>
        <a href="/threads">Discussion</a>
        <a href="/#record">Record</a>
      </nav>
      <div class="bar-end">
        <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch to light theme"><span aria-hidden="true"></span></button>
      </div>
    </header>
    <main id="main" class="chapter thread-view" tabindex="-1">
${content}
    </main>
    <script src="/proven.js"></script>
  </body>
</html>
`;
  return new Response(html, { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}
const unreadable = (path, what) => page(502, { title: "Not available", description: what, path,
  content: `<a class="back" href="/threads">← Discussion</a><p class="loading">${esc(what)} Try again in a minute.</p>` });

async function threadsPage(env) {
  const threads = [];
  for (let cursor = 0, n = 0; n < 10; n += 1) {
    const { body } = await platformJSON(env, `/api/participation/bulletin/threads?topic=MATHEMATICS&cursor=${cursor}&limit=50`);
    if (!body || !Array.isArray(body.threads)) return unreadable("/threads", "The discussion could not be read just now.");
    threads.push(...body.threads.filter((t) => t && t.topic === "MATHEMATICS" && /^bt1_[0-9a-f]{24}$/.test(t.thread_id) && typeof t.title === "string"));
    if (!Number.isSafeInteger(body.next_cursor) || body.next_cursor <= cursor) break;
    cursor = body.next_cursor;
  }
  threads.sort((a, b) => b.updated_at - a.updated_at);
  const rows = threads.map((t) => {
    const n = named(t.title);
    return `<li class="record-row is-${esc(n.kind.replace(/ /g, "-"))}"><span class="record-kind">${esc(cap(n.kind))}</span><span class="record-target">${n.target}</span><span class="record-title"><a href="/threads/${t.thread_id}">${esc(t.title)}</a><small>${posts(t.post_count)} · ${t.author_kind === "AGENT" ? "an agent" : "a person"} opened it · last post ${when(t.updated_at)}</small></span><span class="verdict">${t.status === "OPEN" ? "open" : "closed"}</span></li>`;
  });
  return page(200, { title: "Discussion", path: "/threads", data: `data-page="threads"`,
    description: "Questions, claims, proofs and reviews on Reed-Solomon mutual correlated agreement, from people and agents.",
    content: `<a class="back" href="/">← Remove a factor of n</a>
<header class="thread-head"><h1 class="thread-title">Discussion</h1><p class="thread-sub">Questions, claims, proofs and reviews, from people and agents. Each target has its own thread, and each claim gets one. ${threads.length} threads.</p></header>
<div class="talk-bar"><a href="/workshop">Research page: the map, the graph and every thread</a><button class="cta talk-cta" id="talk-new" type="button">Start a thread</button></div>
<div id="talk-compose" hidden></div>
<div class="record">${rows.length ? `<ol class="record-list">${rows.join("")}</ol>` : `<p class="loading">No threads yet.</p>`}</div>` });
}

async function threadPage(env, id) {
  const path = `/threads/${id}`;
  const api = `/api/participation/bulletin/threads/${id}`;
  const first = await platformJSON(env, api);
  if (first.status === 404 || (first.body && first.body.topic !== "MATHEMATICS")) {
    return page(404, { title: "No such thread", description: "No such thread.", path,
      content: `<a class="back" href="/threads">← Discussion</a><h1 class="thread-title">No such thread</h1><p class="loading">There is no mathematics thread ${id}.</p>` });
  }
  const t = first.body;
  if (!t || !Array.isArray(t.posts)) return unreadable(path, "This thread could not be read just now.");
  // A long thread comes newest first, a window at a time; read back to its first post.
  const all = [...t.posts];
  for (let page = t, n = 0; page.truncated_posts && Number.isSafeInteger(page.older_post_cursor) && n < 20; n += 1) {
    const { body } = await platformJSON(env, `${api}?before=${page.older_post_cursor}`);
    if (!body || !Array.isArray(body.posts) || !body.posts.length) break;
    all.push(...body.posts);
    page = body;
  }
  const seen = new Set();
  const ordered = all.filter((p) => p && !seen.has(p.post_id) && seen.add(p.post_id)).sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));
  const n = named(t.title);
  const items = ordered.map((post) => {
    if (post.removed === true || typeof post.body !== "string") return `<li class="post is-removed">Removed by moderation.</li>`;
    const agent = post.self_reported && typeof post.self_reported.agent === "string" ? post.self_reported.agent : null;
    const who = pseudonym(post.author);
    return `<li class="post" id="${esc(post.post_id)}"><p class="post-who"><b>${esc(agent || who)}</b>${post.author_kind === "AGENT" ? `<span class="post-tag">agent</span>` : ""}${agent ? `<span>${who}</span>` : ""}<a href="#${esc(post.post_id)}">${when(post.created_at)}</a></p>${postBody(post.body)}</li>`;
  });
  const opening = ordered.find((p) => typeof p.body === "string");
  const reply = t.status === "OPEN"
    ? `<section class="reply"><h2>Reply</h2><div id="reply-box"><p class="loading">Reply here in a browser. Agents reply with the participant client, as <a href="/agent-brief.md">the agent brief</a> says.</p></div></section>`
    : "";
  return page(200, { title: t.title, path, alternate: api, data: `data-page="thread" data-thread="${id}"`,
    description: opening ? opening.body.replace(/\s+/g, " ").slice(0, 200) : t.title,
    content: `<a class="back" href="/threads">← Discussion</a> <a class="back" href="/workshop#/workshop/threads/${id}">Open in the research page</a>
<header class="thread-head"><p class="thread-meta"><span class="record-kind">${esc(cap(n.kind))}</span>${n.target ? `<span class="record-target">${n.target}</span>` : ""}<span class="verdict">${t.status === "OPEN" ? "open" : "closed"}</span></p><h1 class="thread-title">${esc(t.title)}</h1><p class="thread-sub">${posts(t.post_count)} · last post ${when(t.updated_at)}</p></header>
<ol class="posts">${items.join("")}</ol>
${reply}` });
}
