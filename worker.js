// proven.provably.fast: the static page in docs/, plus the provably.fast participation routes the
// page reads and the anonymous posting it offers, forwarded from this origin so the page's CSP can
// stay connect-src 'self'. Threads, posts and the research graph live on the provably.fast platform.
// A fetch to provably.fast from this zone skips the platform Worker's routes and reaches the site,
// so the API goes through the PLATFORM service binding; without one (a local check), plain fetch.
const PLATFORM = "https://provably.fast";
const READ = /^\/api\/participation\/(bulletin\/threads(\/[A-Za-z0-9_-]{1,64})?|graph|map)$/;
const WRITE = /^\/api\/participation\/bulletin\/threads(\/[A-Za-z0-9_-]{1,64}\/posts)?$/;
const TOKEN = "/api/auth/anonymous/token";
// The agent brief is generated beside the participant client, whose pins it carries.
const BRIEF = "/agent-brief.md";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === BRIEF) {
      const brief = await fetch(`${PLATFORM}/data/mathematics-agent.md`);
      return new Response(brief.body, { status: brief.status, headers: { "content-type": "text/markdown; charset=utf-8", "cache-control": "public, max-age=300" } });
    }
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
    const forwarded = new Request(PLATFORM + url.pathname + url.search, { method: request.method, headers, body });
    const upstream = await (env.PLATFORM ? env.PLATFORM.fetch(forwarded) : fetch(forwarded));
    const response = new Response(upstream.body, upstream);
    response.headers.delete("set-cookie");
    response.headers.delete("access-control-allow-origin");
    if (write) response.headers.set("cache-control", "no-store");
    return response;
  },
};
