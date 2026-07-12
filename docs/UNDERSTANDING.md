# Understanding

This is a food-and-groceries copilot that lives on Telegram. You tell it
what you want to eat or buy; it figures out the order, checks it with you,
and places it through Swiggy. The human stays in the chat; the machine does
the running around.

Three parts do the work:

- **The brain** is Hermes — an agent framework. It runs on two models: glm
  for thinking, minimax for the fast, chatty replies. Hermes is the thing
  that reads your message, decides what to do, and writes back.
- **The hands** are a Swiggy MCP server. That's the layer that actually
  talks to Swiggy — search restaurants, read the cart, place the order.
  Hermes calls it; the MCP does the touching.
- **The control room** is a small admin app for the human. It's not for
  customers. It's where you watch what the copilot is doing, step in, and
  pull the plug if something looks wrong. Telegram is where the human and
  the copilot talk; the admin app is where the human supervises.

## The three nevers

These are the lines the copilot does not cross. Everything else is
negotiable; these three are not.

1. **Never spend money without a confirm in chat.** Before any order is
   placed, the copilot shows what it's about to do — the restaurant, the
   items, the total — and waits for the human to say yes. No confirm, no
   charge. A cart that pays for itself is a cart that drains your bank
   account at 2am.
2. **Never act as the human without them.** The copilot never sends a
   message as you, never clicks an OAuth grant, never answers a Swiggy OTP.
   It prepares the action; the human takes the last step. If a flow needs
   the human's identity, it stops and asks.
3. **Never keep data the features don't need.** No logging full order
   histories "just in case," no stashing tokens longer than the session
   needs, no keeping address books after the order ships. Keep what the
   feature requires; drop the rest. Memory is a liability, not an asset.

That's the shape of it: a brain that thinks, hands that act, a control
room that watches — and three lines it won't cross.
