import os
import sys
import logging
import discord
from discord.ext import commands

# ==== Config logs (visible in Railway logs) ====
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("discord-bot")

# ==== Read token from environment ====
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.error("DISCORD_TOKEN manquant. Ajoute la variable d'environnement DISCORD_TOKEN dans Railway → Variables.")
    sys.exit(1)

# ==== Intents ====
intents = discord.Intents.default()
# Active si tu veux lire le contenu des messages (pour les commandes prefixées) :
intents.message_content = True

# ==== Bot ====
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    logger.info("Connecté en tant que %s (id=%s)", bot.user, bot.user.id)

# --- Commande simple ---
@bot.command(name="ping")
@commands.cooldown(1, 30.0, commands.BucketType.user)  # 1 usage toutes les 30s par utilisateur
async def ping(ctx: commands.Context):
    await ctx.reply("🏓 pong")

# --- Gestion propre du cooldown ---
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ Patiente {error.retry_after:.1f}s avant de réessayer.", delete_after=6)
    else:
        # Laisse remonter les erreurs inconnues pour les voir dans les logs Railway
        raise error

if __name__ == "__main__":
    bot.run(TOKEN)
