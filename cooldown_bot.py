import os
import time
import logging
import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive

# --- Configuration des logs Render ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Intents et initialisation du bot ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
cooldowns = {}

# --- Commande ping ---
@bot.tree.command(name="ping", description="Tester si le bot répond")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong ! Le bot est en ligne.", ephemeral=True)

# --- Gestion des erreurs globales ---
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

# --- Commande cooldown set ---
@bot.tree.command(name="cooldown_set", description="Définit un cooldown pour un utilisateur (réservé aux modérateurs)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_set(interaction: discord.Interaction, user: discord.Member, seconds: int):
    await interaction.response.defer(ephemeral=True)
    cooldowns.setdefault(interaction.guild_id, {})[user.id] = int(seconds)
    await interaction.followup.send(f"✅ Cooldown de **{int(seconds)}s** appliqué à {user.mention}.", ephemeral=True)
    logging.info(f"[SET] {interaction.user} a défini {seconds}s de cooldown pour {user} dans {interaction.guild.name}")

# --- Commande cooldown remove ---
@bot.tree.command(name="cooldown_remove", description="Supprime le cooldown d'un utilisateur (réservé aux modérateurs)")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_remove(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if user.id in cooldowns.get(interaction.guild_id, {}):
        del cooldowns[interaction.guild_id][user.id]
        await interaction.followup.send(f"🗑️ Cooldown supprimé pour {user.mention}.", ephemeral=True)
        logging.info(f"[REMOVE] {interaction.user} a supprimé le cooldown de {user} dans {interaction.guild.name}")
    else:
        await interaction.followup.send("ℹ️ Aucun cooldown trouvé pour cet utilisateur.", ephemeral=True)

# --- Surveillance des messages ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    guild_id = message.guild.id if message.guild else None
    user_id = message.author.id

    if guild_id in cooldowns and user_id in cooldowns[guild_id]:
        seconds = cooldowns[guild_id][user_id]
        now = time.time()
        last_time = getattr(message.author, "last_message_time", 0)
        if now - last_time < seconds:
            try:
                await message.delete()
                await message.channel.send(
                    f"⏳ {message.author.mention}, attends **{seconds} secondes** avant de renvoyer un message.",
                    delete_after=5,
                )
                logging.info(f"[COOLDOWN] Message supprimé de {message.author} dans {message.channel} ({message.guild.name})")
            except discord.Forbidden:
                logging.warning("Permission insuffisante pour supprimer un message.")
            except Exception as e:
                logging.exception("Erreur lors de la suppression d'un message", exc_info=e)
        else:
            message.author.last_message_time = now

    await bot.process_commands(message)

# --- Démarrage du bot ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    logging.info(f"✅ Connecté en tant que {bot.user} ({bot.user.id})")
    logging.info("Bot prêt à recevoir des commandes.")

keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
