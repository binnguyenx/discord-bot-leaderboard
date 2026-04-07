# Khao bot (skeleton)

## Cây thư mục

```
khao-bot/
  main.py          # chạy bot, sync slash, error handler
  config.py        # DISCORD_TOKEN từ biến môi trường
  db.py            # SQLite init + query
  requirements.txt
  .env.example
  data/            # tự tạo khi chạy
    khao.db
  cogs/
    offers.py      # /offer, /leaderboard, /history, /stats
```

## Schema SQLite

```sql
CREATE TABLE offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  offerer_id INTEGER NOT NULL,
  offeree_id INTEGER NOT NULL,
  amount REAL,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_offers_guild ON offers (guild_id);
CREATE INDEX idx_offers_offerer ON offers (guild_id, offerer_id);
```

## Luồng hoạt động

1. `main.py` khởi tạo bot, gọi `db.init_db()`, load cog `cogs.offers`, `tree.sync()` (slash global).
2. User gọi `/offer` → insert một dòng `offers` (người gọi = offerer, `user` = offeree).
3. `/leaderboard` → `GROUP BY offerer_id` đếm số lần khao.
4. `/history` → danh sách mới nhất; có `user` thì lọc `offerer_id`.
5. `/stats` → tổng số offer + top offerer trong guild.

## Chạy local

```bash
cd khao-bot
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DISCORD_TOKEN='...'   # token bot từ Discord Developer Portal
python main.py
```

Trên [Developer Portal](https://discord.com/developers/applications): bật **Privileged Gateway Intent** nếu sau này cần; MVP slash-only thường không cần `message content`. Mời bot vào server có quyền `applications.commands`.

**Lưu ý:** Slash sync global có thể mất vài phút để hiện trên Discord lần đầu.
