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

export default http;
