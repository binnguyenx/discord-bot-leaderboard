"""Discord bot entrypoint — ghi nhận ai khao ai."""
from __future__ import annotations

import asyncio
import logging
import sys

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN
import db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("khao-bot")


class KhaoBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # Không cần message_content nếu chỉ dùng slash
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.offers")
        synced = await self.tree.sync()
        log.info("Synced %d global app command(s)", len(synced))


bot = KhaoBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if interaction.response.is_done():
        send = interaction.followup.send
    else:
        send = interaction.response.send_message

    if isinstance(error, app_commands.MissingPermissions):
        await send(embed=discord.Embed(title="Lỗi", description="Bạn không đủ quyền.", color=discord.Color.red()), ephemeral=True)
        return
    if isinstance(error, app_commands.CommandInvokeError):
        cause = error.original
        log.exception("Command failed: %s", cause)
        await send(
            embed=discord.Embed(
                title="Lỗi",
                description=f"Lệnh lỗi: `{cause!s}`",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return
    log.exception("App command error: %s", error)
    await send(
        embed=discord.Embed(title="Lỗi", description=str(error), color=discord.Color.red()),
        ephemeral=True,
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """Prefix commands không dùng; báo nhẹ nếu ai gõ !..."""
    if isinstance(error, commands.CommandNotFound):
        return
    log.warning("Prefix error: %s", error)


async def main() -> None:
    if not DISCORD_TOKEN:
        log.error("Thiếu DISCORD_TOKEN. export DISCORD_TOKEN='...' rồi chạy lại.")
        sys.exit(1)
    db.init_db()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
