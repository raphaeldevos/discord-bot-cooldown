import os
import time
import logging
import discord
from discord.ext import commands
from discord import app_commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
cooldowns = {}

@bot.tree.command(name="ping", description="Tester si le bot répond")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong ! Le bot est en ligne.", ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    try:
        msg = f"❌ {error.__class__.__name__}: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass
    logging.exception("Erreur de commande", exc_info=error)

@bot.tree.command(name="cooldown_set", description="Définit un cooldown pour un utilisateur (réservé aux modérateurs)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_set(interaction: discord.Interaction, user: discord.Member, seconds: int):
    await interaction.response.defer(ephemeral=True)
    cooldowns.setdefault(interaction.guild_id, {})[user.id] = int(seconds)
    await interaction.followup.send(f"✅ Cooldown de **{int(seconds)}s** appliqué à {user.mention}.", ephemeral=True)
    logging.info(f"[SET] {interaction.user} → {seconds}s pour {user} @ {interaction.guild.name}")

@bot.tree.command(name="cooldown_remove", description="Supprime le cooldown d'un utilisateur (réservé aux modérateurs)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_remove(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if user.id in cooldowns.get(interaction.guild_id, {}):
        del cooldowns[interaction.guild_id][user.id]
        await interaction.followup.send(f"🗑️ Cooldown supprimé pour {user.mention}.", ephemeral=True)
        logging.info(f"[REMOVE] {interaction.user} a retiré le cooldown de {user} @ {interaction.guild.name}")
    else:
        await interaction.followup.send("ℹ️ Aucun cooldown trouvé pour cet utilisateur.", ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    guild_id = message.guild.id
    user_id = message.author.id
    if guild_id in cooldowns and user_id in cooldowns[guild_id]:
        seconds = cooldowns[guild_id][user_id]
        now = time.time()
        last_time = getattr(message.author, "last_message_time", 0)
        if now - last_time < seconds:
            try:
                await message.delete()
                await message.channel.send(
                    f"⏳ {message.author.mention}, attends **{seconds} s** avant de renvoyer un message.",
                    delete_after=5
                )
                logging.info(f"[CD] Message supprimé de {message.author} dans #{message.channel} ({message.guild.name})")
            except discord.Forbidden:
                logging.warning("Permission insuffisante pour supprimer un message.")
            except Exception as e:
                logging.exception("Erreur suppression message", exc_info=e)
        else:
            message.author.last_message_time = now
    await bot.process_commands(message)

@bot.event
async def on_disconnect():
    logging.warning("⚠️ Déconnecté de la gateway Discord — reconnexion automatique…")

@bot.event
async def on_resumed():
    logging.info("✅ Session Discord reprise (resumed).")

@bot.event
async def on_ready():
    await bot.tree.sync()
    logging.info(f"✅ Connecté en tant que {bot.user} ({bot.user.id}) — prêt.")

bot.run(os.environ["DISCORD_TOKEN"])
