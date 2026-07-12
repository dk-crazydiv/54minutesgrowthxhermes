# Backlog

Work lives here. Finished lines get deleted, because git remembers them.

## Now

- **One live phone check.** Kartik messages the bot from Telegram and gets a reply.
  Everything else about the stand-up is proven (smoke green on all three brains,
  gateway running); this is the last mile only he can do.
- **Gateway survives reboots.** Today it dies with the launching shell. Task: install
  it as a user service (`hermes gateway install` or launchd plist), prove it comes back
  after `stop`/host restart. Proof: status output after a kill.
- **Rotate the Telegram bot token.** It leaked in a board comment once. New token from
  @BotFather, update `~/.hermes/.env`, confirm a live round-trip.

## Next

- **Deliberate routing.** Kill the "No model configured, defaulting to glm-5.2" log
  line: set explicit models per provider, and write the routing choice (which brain for
  which kind of turn) into SOUL.md. Also fix the zai/glm/ZAI naming drift across
  smoke.sh, README, and .odin/config.yaml. Pick one name.
- **Gateway health watcher.** Sibling to the git watcher: ping the bot on a schedule,
  alert on silence. Hermes cron can likely host this.
- **Session cold-start drill.** Fresh session, RESUME.md only, no chat history. Can it
  find the watcher, the scripts, and the state of play? Fix whatever it stumbles on.

## Later

- **More subscriptions as providers.** The seam is
  `plugins/model-providers/<name>/`: a ProviderProfile directory, auto-discovered.
  Any OpenAI-compatible endpoint also works via the `custom` provider today.
- **Skills/tools for real tasks.** Once the brains are stable, give the bot jobs:
  Hermes has cron, memory (MEMORY.md/USER.md), MCP client support out of the box.
