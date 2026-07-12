import { internalMutation } from "./_generated/server";
import { v } from "convex/values";

export const removeSignup = internalMutation({
  args: { email: v.string() },
  handler: async (ctx, { email }) => {
    const doc = await ctx.db
      .query("signups")
      .withIndex("by_email", (q) => q.eq("email", email))
      .unique();
    if (doc) await ctx.db.delete(doc._id);
  },
});
