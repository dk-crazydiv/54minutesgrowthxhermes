import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const http = httpRouter();

http.route({
  path: "/signup",
  method: "OPTIONS",
  handler: httpAction(async () => new Response(null, { status: 204, headers: cors })),
});

http.route({
  path: "/signup",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    try {
      const { email, source } = await req.json();
      const { count } = await ctx.runMutation(api.signups.add, { email, source });
      return Response.json({ ok: true, count }, { headers: cors });
    } catch {
      return Response.json({ ok: false }, { status: 400, headers: cors });
    }
  }),
});

http.route({
  path: "/stats",
  method: "GET",
  handler: httpAction(async (ctx) => {
    const count = await ctx.runQuery(api.signups.count, {});
    return Response.json({ count }, { headers: cors });
  }),
});

// --- Agent endpoints (key-protected, query-param style) ---

function authed(req: Request): boolean {
  const key = process.env.AGENT_KEY;
  return !!key && req.headers.get("X-Agent-Key") === key;
}
const deny = () => Response.json({ ok: false, error: "unauthorized" }, { status: 401 });

http.route({
  path: "/u/history",
  method: "GET",
  handler: httpAction(async (ctx, req) => {
    if (!authed(req)) return deny();
    const url = new URL(req.url);
    const userId = url.searchParams.get("id");
    if (!userId) return Response.json({ ok: false, error: "id required" }, { status: 400 });
    const limit = Math.max(1, Math.min(500, Number(url.searchParams.get("limit") ?? 20) || 20));
    const orders = await ctx.runQuery(api.users.history, { userId, limit });
    return Response.json({ ok: true, count: orders.length, orders });
  }),
});

http.route({
  path: "/u/doc",
  method: "GET",
  handler: httpAction(async (ctx, req) => {
    if (!authed(req)) return deny();
    const url = new URL(req.url);
    const userId = url.searchParams.get("id");
    const kind = url.searchParams.get("kind");
    if (!userId || !kind) return Response.json({ ok: false, error: "id and kind required" }, { status: 400 });
    const doc = await ctx.runQuery(api.users.getDoc, { userId, kind });
    if (!doc) return Response.json({ ok: false, error: "not found" }, { status: 404 });
    return new Response(doc.content, { headers: { "Content-Type": "text/markdown" } });
  }),
});

http.route({
  path: "/u/doc",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authed(req)) return deny();
    const url = new URL(req.url);
    const userId = url.searchParams.get("id");
    if (!userId) return Response.json({ ok: false, error: "id required" }, { status: 400 });
    try {
      const { kind, content } = await req.json();
      const res = await ctx.runMutation(api.users.upsertDoc, { userId, kind, content });
      return Response.json({ ok: true, ...res });
    } catch {
      return Response.json({ ok: false }, { status: 400 });
    }
  }),
});

http.route({
  path: "/u/orders/bulk",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    if (!authed(req)) return deny();
    const url = new URL(req.url);
    const userId = url.searchParams.get("id");
    if (!userId) return Response.json({ ok: false, error: "id required" }, { status: 400 });
    try {
      const { orders } = await req.json();
      const res = await ctx.runMutation(api.users.bulkUpsertOrders, { userId, orders });
      return Response.json({ ok: true, ...res });
    } catch (e) {
      return Response.json({ ok: false, error: String(e) }, { status: 400 });
    }
  }),
});

export default http;
