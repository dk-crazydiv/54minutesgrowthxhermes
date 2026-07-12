import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

export const clearUser = internalMutation({
  args: { userId: v.string() },
  handler: async (ctx, { userId }) => {
    const orders = await ctx.db.query("orders")
      .withIndex("by_user_date", (q) => q.eq("userId", userId)).collect();
    for (const o of orders) await ctx.db.delete(o._id);
    const docs = await ctx.db.query("userDocs")
      .withIndex("by_user_kind", (q) => q.eq("userId", userId)).collect();
    for (const d of docs) await ctx.db.delete(d._id);
    return { orders: orders.length, docs: docs.length };
  },
});
