import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const add = mutation({
  args: { email: v.string(), source: v.optional(v.string()) },
  handler: async (ctx, { email, source }) => {
    const clean = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(clean)) throw new Error("invalid email");
    const existing = await ctx.db
      .query("signups")
      .withIndex("by_email", (q) => q.eq("email", clean))
      .unique();
    if (!existing) await ctx.db.insert("signups", { email: clean, source });
    const count = (await ctx.db.query("signups").collect()).length;
    return { count };
  },
});

export const count = query({
  args: {},
  handler: async (ctx) => (await ctx.db.query("signups").collect()).length,
});
