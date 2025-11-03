import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from keep_alive import keep_alive

keep_alive()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

_last_msg = {}
cooldowns = {}

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Erreur de sync:", e)
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    if message.author.guild_permissions.manage_messages:
        return
    guild_id = message.guild.id
    user_id = message.author.id
    ch_id = message.channel.id
    now = datetime.now(timezone.utc)
    cooldown = cooldowns.get(guild_id, {}).get(user_id)
    if cooldown:
        last = _last_msg.get((guild_id, user_id, ch_id))
        if last and (now - last).total_seconds() < cooldown:
            try:
                await message.delete()
                await message.channel.send(
                    f"⏳ {message.author.mention}, attends encore **{int(cooldown - (now - last).total_seconds())}s**.",
                    delete_after=5)
            except Exception:
                pass
            return
    _last_msg[(guild_id, user_id, ch_id)] = now
    await bot.process_commands(message)

class Cooldown(app_commands.Group):
    def __init__(self):
        super().__init__(name="cooldown", description="Gère les délais individuels")

    @app_commands.command(name="set")
    async def set_(self, interaction: discord.Interaction, user: discord.Member, seconds: int):
        cooldowns.setdefault(interaction.guild_id, {})[user.id] = seconds
        await interaction.response.send_message(f"✅ Cooldown de **{seconds}s** appliqué à {user.mention}.")

    @app_commands.command(name="remove")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        if user.id in cooldowns.get(interaction.guild_id, {}):
            del cooldowns[interaction.guild_id][user.id]
            await interaction.response.send_message(f"🗑️ Cooldown supprimé pour {user.mention}.")
        else:
            await interaction.response.send_message("ℹ️ Aucun cooldown trouvé.")

bot.tree.add_command(Cooldown())

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("⚠️ Le token du bot n'est pas défini.")
    else:
        bot.run(token)
