"""Slash commands: offer, leaderboard, history, stats."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db

_NAME_MAX = 20


def _embed_ok(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.green())


def _embed_err(msg: str) -> discord.Embed:
    return discord.Embed(title="Lỗi", description=msg, color=discord.Color.red())


def _trunc(s: str, max_len: int) -> str:
    s = str(s).strip()
    if len(s) <= max_len:
        return s
    if max_len <= 1:
        return s[:max_len]
    return s[: max_len - 1] + "…"


def _norm_term(term: str) -> str:
    t = (term or "").strip().lower()
    return t or "summer"


def _text_block(lines: list[str]) -> str:
    return "```text\n" + "\n".join(lines) + "\n```"


def _display_name(guild: discord.Guild, user_id: int) -> str:
    m = guild.get_member(user_id)
    if m:
        return _trunc(m.display_name, _NAME_MAX)
    return _trunc(f"User {user_id}", _NAME_MAX)


def _leaderboard_table(guild: discord.Guild, rows: list[dict]) -> str:
    header = f"{'#':<2} {'User':<{_NAME_MAX}} {'Count':>5}"
    sep = f"{'--':<2} {'-' * _NAME_MAX} {'-' * 5}"
    out = [header, sep]
    for i, r in enumerate(rows, start=1):
        m = guild.get_member(r["offerer_id"])
        name = m.display_name if m else f"User {r['offerer_id']}"
        name = _trunc(name, _NAME_MAX)
        out.append(f"{i:<2} {name:<{_NAME_MAX}} {int(r['count']):>5}")
    return _text_block(out)


def _history_table(guild: discord.Guild, rows: list[dict]) -> str:
    w_id, w_company, w_term, w_count, w_note = 5, 18, 10, 7, 20
    header = (
        f"{'ID':<{w_id}} "
        f"{'Offerer':<{_NAME_MAX}} "
        f"{'Offeree':<{_NAME_MAX}} "
        f"{'Company':<{w_company}} "
        f"{'Term':<{w_term}} "
        f"{'Count':>{w_count}} "
        f"{'Note':<{w_note}}"
    )
    sep = (
        f"{'-' * w_id} "
        f"{'-' * _NAME_MAX} "
        f"{'-' * _NAME_MAX} "
        f"{'-' * w_company} "
        f"{'-' * w_term} "
        f"{'-' * w_count} "
        f"{'-' * w_note}"
    )
    out = [header, sep]
    for o in rows:
        o_name = _display_name(guild, o["offerer_id"])
        e_name = _display_name(guild, o["offeree_id"])
        company = _trunc((o.get("company") or "—"), w_company)
        term = _trunc((o.get("term") or "—"), w_term)
        cnt = int(o.get("count") or 1)
        note = (o["note"] or "").strip() or "—"
        note = _trunc(note, w_note)
        out.append(
            f"{int(o['id']):<{w_id}} "
            f"{o_name:<{_NAME_MAX}} "
            f"{e_name:<{_NAME_MAX}} "
            f"{company:<{w_company}} "
            f"{term:<{w_term}} "
            f"{cnt:>{w_count}} "
            f"{note:<{w_note}}"
        )
    return _text_block(out)


def _detail_table(rows: list[dict]) -> str:
    w_company, w_term, w_count = 24, 10, 7
    header = (
        f"{'Company':<{w_company}} "
        f"{'Term':<{w_term}} "
        f"{'Count':>{w_count}}"
    )
    sep = (
        f"{'-' * w_company} "
        f"{'-' * w_term} "
        f"{'-' * w_count}"
    )
    out = [header, sep]
    for r in rows:
        company = _trunc(r.get("company", "—"), w_company)
        term = _trunc(r.get("term", "—"), w_term)
        cnt = int(r.get("cnt", 0))
        out.append(f"{company:<{w_company}} {term:<{w_term}} {cnt:>{w_count}}")
    return _text_block(out)


def _stats_table(guild: discord.Guild, s: dict) -> str:
    w_key, w_val = 20, 24
    header = f"{'Metric':<{w_key}} {'Value':<{w_val}}"
    sep = f"{'-' * w_key} {'-' * w_val}"
    total = str(s["total_offers"])
    if s["top_offerer_id"] is None:
        top_val = "Chưa có ai khao."
    else:
        m = guild.get_member(s["top_offerer_id"])
        name = m.display_name if m else str(s["top_offerer_id"])
        name = _trunc(name, 16)
        top_val = f"{name} — {s['top_count']} lần"
    top_val = _trunc(top_val, w_val)
    rows = [
        header,
        sep,
        f"{'Tổng offer':<{w_key}} {total:<{w_val}}",
        f"{'Số record':<{w_key}} {str(s['total_records']):<{w_val}}",
        f"{'Top khao':<{w_key}} {top_val:<{w_val}}",
    ]
    return _text_block(rows)


class LeaderboardDetailSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, term: str, rows: list[dict[str, int]]) -> None:
        options: list[discord.SelectOption] = []
        for r in rows:
            uid = int(r["offerer_id"])
            count = int(r["count"])
            label = _display_name(guild, uid)
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(uid),
                    description=f"{count} offer",
                )
            )
        super().__init__(
            placeholder="Chọn user để xem chi tiết company/term",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.term = term

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Lệnh chỉ dùng trong server.", ephemeral=True)
            return
        uid = int(self.values[0])
        breakdown = db.offerer_offer_breakdown(
            interaction.guild.id,
            uid,
            self.term,
            limit=20,
        )
        if not breakdown:
            await interaction.response.send_message(
                embed=_embed_ok("Chi tiết offer", f"Không có offer cho term `{self.term}`."),
                ephemeral=True,
            )
            return
        total = sum(int(x["cnt"]) for x in breakdown)
        name = _display_name(interaction.guild, uid)
        desc = _detail_table(breakdown)
        desc += f"\nTop `{name}`: **`{total}`** offer trong term `{self.term}`."
        await interaction.response.send_message(
            embed=_embed_ok(f"Chi tiết {name}", desc),
            ephemeral=True,
        )


class LeaderboardDetailView(discord.ui.View):
    def __init__(self, owner_id: int, guild: discord.Guild, term: str, rows: list[dict[str, int]]) -> None:
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.add_item(LeaderboardDetailSelect(guild, term, rows))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Chỉ người gọi lệnh mới dùng menu này.",
                ephemeral=True,
            )
            return False
        return True


class OffersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="offer", description="Ghi nhận một lần khao")
    @app_commands.describe(
        user="Người được khao",
        company="Tên công ty",
        term="Kỳ (ví dụ: summer)",
        note="Ghi chú (tuỳ chọn)",
    )
    async def offer(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        company: str,
        term: str = "summer",
        note: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                embed=_embed_err("Không thể khao chính mình."),
                ephemeral=True,
            )
            return
        company = _trunc(company.strip(), 80)
        term = _norm_term(term)
        if not company:
            await interaction.response.send_message(
                embed=_embed_err("`company` không được để trống."),
                ephemeral=True,
            )
            return
        try:
            result = db.add_or_increment_offer(
                interaction.guild.id,
                interaction.user.id,
                user.id,
                company,
                term,
                note,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi lưu DB: {e}"),
                ephemeral=True,
            )
            return
        action = "Tao moi" if bool(result["created"]) else "Cong don"
        desc = (
            f"{action} record `#{result['id']}`: {interaction.user.mention} -> {user.mention}\n"
            f"`{company}` | term `{term}` | count hien tai: **`{result['count']}`**"
        )
        if note:
            desc += f"\n_{note[:200]}_"
        await interaction.response.send_message(embed=_embed_ok("Offer", desc))

    @app_commands.command(name="leaderboard", description="Top người khao nhiều nhất")
    @app_commands.describe(term="Kỳ muốn xem (mặc định: summer)")
    async def leaderboard_cmd(self, interaction: discord.Interaction, term: str = "summer") -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        term = _norm_term(term)
        try:
            rows = db.leaderboard(interaction.guild.id, term=term, limit=10)
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi DB: {e}"),
                ephemeral=True,
            )
            return
        if not rows:
            await interaction.response.send_message(
                embed=_embed_ok("Leaderboard", f"Chưa có offer nào trong term `{term}`. Tất cả đang `0`."),
            )
            return
        g = interaction.guild
        top = rows[0]
        top_name = _display_name(g, int(top["offerer_id"]))
        top_count = int(top["count"])
        desc = _leaderboard_table(g, rows)
        desc += f"\nTop term `{term}`: **{top_name}** — `{top_count}` offer. Khao di an thoi."
        view = LeaderboardDetailView(interaction.user.id, g, term, rows)
        await interaction.response.send_message(
            embed=_embed_ok(f"Leaderboard ({term})", desc),
            view=view,
        )

    @app_commands.command(name="history", description="Lịch sử khao gần đây")
    @app_commands.describe(
        user="Lọc theo người khao (để trống = cả server)",
        term="Lọc theo kỳ (để trống = tất cả kỳ)",
    )
    async def history_cmd(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
        term: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        oid = user.id if user else None
        t = _norm_term(term) if term else None
        try:
            rows = db.history(interaction.guild.id, offerer_id=oid, term=t, limit=15)
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi DB: {e}"),
                ephemeral=True,
            )
            return
        if not rows:
            await interaction.response.send_message(
                embed=_embed_ok("History", "Không có bản ghi."),
            )
            return
        title = f"History ({user.display_name})" if user else "History (server)"
        if t:
            title += f" - {t}"
        await interaction.response.send_message(
            embed=_embed_ok(title, _history_table(interaction.guild, rows)),
        )

    @app_commands.command(name="stats", description="Thống kê nhanh server")
    @app_commands.describe(term="Kỳ muốn xem (mặc định: summer)")
    async def stats_cmd(self, interaction: discord.Interaction, term: str = "summer") -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        term = _norm_term(term)
        try:
            s = db.stats(interaction.guild.id, term=term)
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi DB: {e}"),
                ephemeral=True,
            )
            return
        if s["total_offers"] == 0:
            desc = f"Không có offer trong term `{term}`. Tất cả đang `0`."
            await interaction.response.send_message(embed=_embed_ok("Stats", desc))
            return
        await interaction.response.send_message(
            embed=_embed_ok(f"Stats ({term})", _stats_table(interaction.guild, s)),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OffersCog(bot))
