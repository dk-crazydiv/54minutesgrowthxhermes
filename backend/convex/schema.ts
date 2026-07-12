import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  signups: defineTable({
    email: v.string(),
    source: v.optional(v.string()),
  }).index("by_email", ["email"]),
  orders: defineTable({
    userId: v.string(),
    date: v.string(),
    time: v.string(),
    restaurant: v.string(),
    restaurantArea: v.string(),
    items: v.string(),
    amountInr: v.number(),
    status: v.string(),
    orderId: v.string(),
    resId: v.string(),
  })
    .index("by_user_date", ["userId", "date"])
    .index("by_user_order", ["userId", "orderId"]),
  userDocs: defineTable({
    userId: v.string(),
    kind: v.string(), // 'preferences' | 'stats' | 'profile' | 'notes'
    content: v.string(),
    updatedAt: v.number(),
  }).index("by_user_kind", ["userId", "kind"]),
});
