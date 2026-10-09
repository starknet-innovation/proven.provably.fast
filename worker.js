// A challenge's own site (data/campaigns.json "site"), served by this one Worker for every
// challenge: its export copies this file next to the site's wrangler.jsonc, which names the
// challenge (vars.SITE_CAMPAIGN), its domain, the PLATFORM binding to provably.fast's API Worker
// (services/auth) and the THREADS binding to its thread pages (research/discovery/thread-pages).
// Everything else comes from the registry entry, so a new challenge site needs no code:
// docs/CHALLENGE_SITES.md.
//
// - The site's own files (docs/, its landing page) are served first, by Cloudflare.
// - /workshop is provably.fast's research page itself: the same files, read from provably.fast,
//   told which challenge this is (<meta name="pf-site">), titled for it. Without a landing
//   page it is also the home page.
// - /threads and /threads/ID are provably.fast's thread pages, rendered for this site's board
//   (any reader, no script); /agent-brief.md is the challenge's agent brief.
// - /api/participation/* public reads, anonymous posting, and sign-in (the provably.fast
//   session, whose cookie covers this subdomain) go to the platform through the binding: a
//   fetch to provably.fast from this zone would skip that Worker and reach the static site.
const PLATFORM = "https://provably.fast";
const THREAD_PAGE = /^\/threads\/(bt1_[0-9a-f]{24})$/;
// The research page's own files, where this site has none of the same name.
const APP_FILE = /^\/([a-z0-9-]+\.(js|css)|assets\/[A-Za-z0-9._\/-]{1,120}|data\/[A-Za-z0-9._\/-]{1,120})$/;
// Public reads only: no credential is ever forwarded on a read.
const READ = /^\/api\/participation\/[A-Za-z0-9_\/-]{1,200}$/;
const ANONYMOUS_WRITE = /^\/api\/participation\/bulletin\/threads(\/[A-Za-z0-9_-]{1,64}\/posts)?$/;
const TOKEN = "/api/auth/anonymous/token";
// The provably.fast session's own routes a site needs: who is signed in, signing in and out,
// and posting as them. Each POST must come from this site's own pages.
const SESSION_READ = new Set(["/api/auth/status", "/api/auth/identity"]);
const SESSION_WRITE = /^\/api\/auth\/(sign-in\/social|sign-out|bulletin\/threads|bulletin\/volunteers\/release|bulletin\/threads\/[A-Za-z0-9_-]{1,64}\/(posts|volunteer|close))$/;
const SESSION_COOKIE = /^(__Secure-)?pvfast\./;

const platform = (env, request) => (env.PLATFORM ? env.PLATFORM.fetch(request) : fetch(request));
const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// The challenge's registry entry, read from provably.fast and kept for five minutes.
let registry = { at: 0, entry: null };
async function challenge(env) {
  if (registry.entry && Date.now() - registry.at < 300_000) return registry.entry;
  try {
    const response = await fetch(`${PLATFORM}/data/campaigns.json`);
    const entry = response.ok ? (await response.json()).campaigns.find((c) => c.campaign_id === env.SITE_CAMPAIGN && c.site) : null;
    if (entry) registry = { at: Date.now(), entry };
  } catch { /* keep the last entry read */ }
  return registry.entry;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const reading = request.method === "GET" || request.method === "HEAD";
    if (reading && url.pathname === "/agent-brief.md") {
      const entry = await challenge(env);
      if (!entry) return new Response("The agent brief is unavailable just now.", { status: 502 });
      const brief = await fetch(`${PLATFORM}/data/${entry.brief}`);
      return new Response(brief.body, { status: brief.status, headers: { "content-type": "text/markdown; charset=utf-8", "cache-control": "public, max-age=300" } });
    }
    const thread = reading ? url.pathname.match(THREAD_PAGE) : null;
    if (thread || (reading && (url.pathname === "/threads" || url.pathname === "/threads/"))) {
      const upstream = await env.THREADS.fetch(new Request(PLATFORM + url.pathname, { method: request.method, headers: { accept: "text/html", "x-pf-site": env.SITE_CAMPAIGN } }));
      return new Response(upstream.body, { status: upstream.status, headers: pick(upstream.headers, ["content-type", "cache-control", "location"]) });
    }
    if (reading && (url.pathname === "/workshop" || url.pathname === "/workshop/")) return workshop(request, env);
    if (reading && url.pathname === "/") {
      const own = await env.ASSETS.fetch(request);
      return own.status === 404 ? workshop(request, env) : own;
    }
    if (reading && APP_FILE.test(url.pathname)) {
      const own = await env.ASSETS.fetch(request);
      return own.status === 404 ? fetch(PLATFORM + url.pathname, { method: request.method }) : own;
    }
    if (url.pathname.startsWith("/api/auth/")) return session(request, env, url);
    const read = request.method === "GET" && READ.test(url.pathname);
    const write = request.method === "POST" && ANONYMOUS_WRITE.test(url.pathname);
    if (!read && !write) {
      if (url.pathname.startsWith("/api/")) return new Response("Not found", { status: 404 });
      return env.ASSETS.fetch(request);
    }
    // Only what the platform needs: no cookies, and the bearer only on writes.
    const headers = { accept: "application/json" };
    if (write) {
      headers["content-type"] = "application/json";
      const bearer = request.headers.get("authorization");
      if (bearer) headers.authorization = bearer;
    }
    return forward(request, env, url, headers, write);
  },
};

function pick(source, names) {
  const headers = new Headers();
  for (const name of names) if (source.has(name)) headers.set(name, source.get(name));
  return headers;
}

async function forward(request, env, url, headers, write, keepCookies = false) {
  const body = write ? await request.text() : undefined;
  if (body !== undefined && body.length > 65_536) return new Response("Too large", { status: 413 });
  const upstream = await platform(env, new Request(PLATFORM + url.pathname + url.search, { method: request.method, headers, body }));
  const response = new Response(upstream.body, upstream);
  if (!keepCookies) response.headers.delete("set-cookie");
  response.headers.delete("access-control-allow-origin");
  if (write || keepCookies) response.headers.set("cache-control", "no-store");
  return response;
}

// The provably.fast session, presented from this site: only its own cookie goes up, a POST only
// from this site's pages (the platform checks the Origin again), and the visitor's address so
// its rate limits count them alone. Signing in names this site, so the platform returns here.
async function session(request, env, url) {
  if (request.method === "POST" && url.pathname === TOKEN) {
    return forward(request, env, url, { accept: "application/json", "content-type": "application/json" }, true);
  }
  if (request.method === "GET" && url.pathname === "/api/auth/account") {
    return Response.redirect(`${PLATFORM}/api/auth/account`, 302);
  }
  const read = request.method === "GET" && SESSION_READ.has(url.pathname);
  const write = request.method === "POST" && SESSION_WRITE.test(url.pathname);
  if (!read && !write) return new Response("Not found", { status: 404 });
  const origin = request.headers.get("origin");
  if (write && origin !== url.origin) return Response.json({ schema_version: 1, error: { code: "ORIGIN_REQUIRED" } }, { status: 403 });
  const headers = { accept: "application/json" };
  const cookie = (request.headers.get("cookie") || "").split(/;\s*/).filter((pair) => SESSION_COOKIE.test(pair)).join("; ");
  if (cookie) headers.cookie = cookie;
  const visitor = request.headers.get("cf-connecting-ip");
  if (visitor) headers["cf-connecting-ip"] = visitor;
  if (!write) return forward(request, env, url, headers, false, true);
  headers.origin = origin;
  headers["content-type"] = "application/json";
  if (url.pathname === "/api/auth/sign-in/social") {
    let body;
    try { body = JSON.parse(await request.text()); } catch { body = null; }
    if (!body || Object.keys(body).join(",") !== "provider") return Response.json({ schema_version: 1, error: { code: "SIGN_IN_OPTIONS_INVALID" } }, { status: 400 });
    const upstream = await platform(env, new Request(PLATFORM + url.pathname, { method: "POST", headers, body: JSON.stringify({ provider: body.provider, return_to: env.SITE_CAMPAIGN }) }));
    const response = new Response(upstream.body, upstream);
    response.headers.set("cache-control", "no-store");
    return response;
  }
  return forward(request, env, url, headers, true, true);
}

// provably.fast's research page, for this site's challenge: the same files, named and titled.
async function workshop(request, env) {
  const [upstream, entry, card] = await Promise.all([fetch(`${PLATFORM}/`), challenge(env),
    env.ASSETS.fetch(new Request(new URL("/og.png", request.url))).then((r) => r.ok).catch(() => false)]);
  if (!upstream.ok) return new Response("The research page is unavailable just now.", { status: 502 });
  const host = new URL(request.url).host;
  let html = (await upstream.text()).replace("<head>", `<head>\n    <meta name="pf-site" content="${esc(env.SITE_CAMPAIGN)}">`);
  if (entry) {
    const set = (attribute, name, value) => {
      html = html.replace(new RegExp(`(<meta ${attribute}="${name}" content=")[^"]*(")`), `$1${esc(value)}$2`);
    };
    html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(entry.title)} · ${esc(host)}</title>`);
    set("name", "description", entry.note);
    set("property", "og:url", `https://${host}/workshop`);
    set("property", "og:site_name", host);
    for (const [attribute, prefix] of [["property", "og"], ["name", "twitter"]]) {
      set(attribute, `${prefix}:title`, entry.title);
      set(attribute, `${prefix}:description`, entry.note);
      if (card) set(attribute, `${prefix}:image`, `https://${host}/og.png`);
    }
    if (card) set("property", "og:image:alt", entry.title);
  }
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-cache" } });
}
