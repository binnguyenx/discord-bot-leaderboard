# Khao Bot

A lightweight Discord slash-command bot to track internship/job offers by user, company, and term.

## Features

- Record offers with `/offer` using:
  - offerer (command user)
  - offeree (target user)
  - company
  - term (for example: `summer`)
  - optional note
- Upsert behavior: if `(offerer + offeree + company + term)` already exists, the bot increments `count` instead of creating a new row.
- Leaderboard by term (`/leaderboard`) with:
  - table-style output (`User | Count`)
  - top offerer highlight
  - select menu to view per-user breakdown (`company | term | count`)
- History view (`/history`) with optional user and term filters.
- Stats view (`/stats`) with total offers, total records, and top offerer.

## Project Structure

```text
khao-bot/
  main.py              # bot entrypoint, extension loading, slash sync, error handling
  config.py            # DISCORD_TOKEN from env/.env
  db.py                # SQLite schema, migration, and queries
  requirements.txt
  data/
    khao.db            # auto-created on first run
  cogs/
    offers.py          # slash commands: /offer, /leaderboard, /history, /stats
```

## SQLite Schema (Current)

```sql
CREATE TABLE offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  offerer_id INTEGER NOT NULL,
  offeree_id INTEGER NOT NULL,
  company TEXT,
  term TEXT,
  note TEXT,
  count INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_offers_guild ON offers (guild_id);
CREATE INDEX idx_offers_offerer ON offers (guild_id, offerer_id);
CREATE INDEX idx_offers_term ON offers (guild_id, term);
CREATE INDEX idx_offers_match ON offers (guild_id, offerer_id, offeree_id, company, term);
```

`db.init_db()` includes backward-compatible migration (adds missing columns/indexes for older databases).

## Commands

- `/offer user:<member> company:<text> term:<text> note:<text optional>`
- `/leaderboard term:<text = summer by default>`
- `/history user:<member optional> term:<text optional>`
- `/stats term:<text = summer by default>`

## Run Locally

```bash
cd khao-bot
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DISCORD_TOKEN='your_bot_token'
python main.py
```

If login/sync is successful, logs should include:

- `Synced ... app command(s)`
- `connected to Gateway`

## Discord Setup Notes

- Create/invite your bot from the [Discord Developer Portal](https://discord.com/developers/applications).
- Required scopes for invite URL:
  - `bot`
  - `applications.commands`
- Slash commands are synced globally, so first-time updates can take a few minutes to appear.
