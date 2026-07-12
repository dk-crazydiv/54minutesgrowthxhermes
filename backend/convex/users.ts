import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const orderFields = {
  date: v.string(),
  time: v.string(),
  restaurant: v.string(),
  restaurantArea: v.string(),
  items: v.string(),
  amountInr: v.number(),
  status: v.string(),
  orderId: v.string(),
  resId: v.string(),
};

export const bulkUpsertOrders = mutation({
  args: { userId: v.string(), orders: v.array(v.object(orderFields)) },
  handler: async (ctx, { userId, orders }) => {
    let inserted = 0;
    let updated = 0;
    for (const o of orders) {
      const existing = await ctx.db
        .query("orders")
        .withIndex("by_user_order", (q) =>
          q.eq("userId", userId).eq("orderId", o.orderId)
        )
        .unique();
      if (existing) {
        await ctx.db.patch(existing._id, o);
        updated++;
      } else {
        await ctx.db.insert("orders", { userId, ...o });
        inserted++;
      }
    }
    const total = (
      await ctx.db
        .query("orders")
        .withIndex("by_user_date", (q) => q.eq("userId", userId))
        .collect()
    ).length;
    return { inserted, updated, total };
  },
});

export const history = query({
  args: { userId: v.string(), limit: v.optional(v.number()) },
  handler: async (ctx, { userId, limit }) => {
    return await ctx.db
      .query("orders")
      .withIndex("by_user_date", (q) => q.eq("userId", userId))
      .order("desc")
      .take(limit ?? 20);
  },
});

export const upsertDoc = mutation({
  args: { userId: v.string(), kind: v.string(), content: v.string() },
  handler: async (ctx, { userId, kind, content }) => {
    const existing = await ctx.db
      .query("userDocs")
      .withIndex("by_user_kind", (q) => q.eq("userId", userId).eq("kind", kind))
      .unique();
    const updatedAt = Date.now();
    if (existing) {
      await ctx.db.patch(existing._id, { content, updatedAt });
      return { updated: true };
    }
    await ctx.db.insert("userDocs", { userId, kind, content, updatedAt });
    return { updated: false };
  },
});

export const getDoc = query({
  args: { userId: v.string(), kind: v.string() },
  handler: async (ctx, { userId, kind }) => {
    return await ctx.db
      .query("userDocs")
      .withIndex("by_user_kind", (q) => q.eq("userId", userId).eq("kind", kind))
      .unique();
  },
});
