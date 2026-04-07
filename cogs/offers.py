"""Slash commands: offer, leaderboard, history, stats."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import db


def _embed_ok(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.green())


def _embed_err(msg: str) -> discord.Embed:
    return discord.Embed(title="Lỗi", description=msg, color=discord.Color.red())


def _fmt_offer_line(
    o: dict,
    guild: discord.Guild,
) -> str:
    offerer = guild.get_member(o["offerer_id"])
    offeree = guild.get_member(o["offeree_id"])
    o_name = offerer.mention if offerer else f"<@{o['offerer_id']}>"
    e_name = offeree.mention if offeree else f"<@{o['offeree_id']}>"
    amt = o["amount"]
    amt_s = f"{amt:g}" if amt is not None else "—"
    note = (o["note"] or "").strip() or "—"
    return f"`#{o['id']}` {o_name} → {e_name} | `{amt_s}` | {note[:80]}"


class OffersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="offer", description="Ghi nhận một lần khao")
    @app_commands.describe(
        user="Người được khao",
        amount="Số tiền (tuỳ chọn)",
        note="Ghi chú (tuỳ chọn)",
    )
    async def offer(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: float | None = None,
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
        try:
            oid = db.add_offer(
                interaction.guild.id,
                interaction.user.id,
                user.id,
                amount,
                note,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi lưu DB: {e}"),
                ephemeral=True,
            )
            return
        desc = f"Đã ghi nhận `#{oid}`: {interaction.user.mention} khao {user.mention}"
        if amount is not None:
            desc += f" — `{amount:g}`"
        if note:
            desc += f"\n_{note[:200]}_"
        await interaction.response.send_message(embed=_embed_ok("Offer", desc))

    @app_commands.command(name="leaderboard", description="Top người khao nhiều nhất")
    async def leaderboard_cmd(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        try:
            rows = db.leaderboard(interaction.guild.id, limit=10)
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi DB: {e}"),
                ephemeral=True,
            )
            return
        if not rows:
            await interaction.response.send_message(
                embed=_embed_ok("Leaderboard", "Chưa có offer nào."),
            )
            return
        lines = []
        for i, r in enumerate(rows, start=1):
            m = interaction.guild.get_member(r["offerer_id"])
            name = m.display_name if m else f"User {r['offerer_id']}"
            lines.append(f"**{i}.** {name} — `{r['count']}` lần khao")
        await interaction.response.send_message(
            embed=_embed_ok("Leaderboard", "\n".join(lines)),
        )

    @app_commands.command(name="history", description="Lịch sử khao gần đây")
    @app_commands.describe(user="Lọc theo người khao (để trống = cả server)")
    async def history_cmd(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        oid = user.id if user else None
        try:
            rows = db.history(interaction.guild.id, offerer_id=oid, limit=15)
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
        lines = [_fmt_offer_line(o, interaction.guild) for o in rows]
        title = f"History ({user.display_name})" if user else "History (server)"
        await interaction.response.send_message(
            embed=_embed_ok(title, "\n".join(lines)),
        )

    @app_commands.command(name="stats", description="Thống kê nhanh server")
    async def stats_cmd(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=_embed_err("Lệnh chỉ dùng trong server."),
                ephemeral=True,
            )
            return
        try:
            s = db.stats(interaction.guild.id)
        except Exception as e:
            await interaction.response.send_message(
                embed=_embed_err(f"Lỗi DB: {e}"),
                ephemeral=True,
            )
            return
        top_line = "Chưa có ai khao."
        if s["top_offerer_id"] is not None:
            m = interaction.guild.get_member(s["top_offerer_id"])
            name = m.display_name if m else str(s["top_offerer_id"])
            top_line = f"**{name}** — `{s['top_count']}` lần"
        desc = (
            f"Tổng offer: **`{s['total_offers']}`**\n"
            f"Số bản ghi: **`{s['total_offers']}`**\n"
            f"Top khao: {top_line}"
        )
        await interaction.response.send_message(embed=_embed_ok("Stats", desc))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OffersCog(bot))
