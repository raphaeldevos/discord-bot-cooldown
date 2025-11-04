import os
import time
import json
import logging
import discord
from discord.ext import commands
from discord import app_commands

# ---- keep_alive : compatible Render ($PORT) ----
# (garde le service web vivant en mode Web Service ; inutile mais inoffensif en Worker)
try:
    from flask import Flask, request
    from threading import Thread

    app = Flask(__name__)

    @app.get("/")
    def home():
        return "Bot en ligne ✅", 200

    def _run_keepalive():
        port = int(os.getenv("PORT", "8080"))
        app.run(host="0.0.0.0", port=port)

    def keep_alive():
        t = Thread(target=_run_keepalive, daemon=True)
        t.start()
except Exception:
    # Si Flask absent (ex: mode Worker), on ignore
    def keep_alive():
        pass

# ---- Logs propres pour Render ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---- Fichier JSON de persistance ----
COOLDOWN_FILE = os.getenv("COOLDOWN_FILE", "cooldowns.json")

def load_cooldowns():
    """Charge {guild_id: {user_id: seconds}} depuis JSON."""
    if not os.path.exists(COOLDOWN_FILE):
        return {}
    try:
        with open(COOLDOWN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # clés JSON -> int
        return {int(g): {int(u): int(s) for u, s in users.items()} for g, users in data.items()}
    except Exception as e:
        logging.exception("Impossible de lire %s (reset en mémoire).", COOLDOWN_FILE, exc_info=e)
        return {}

def save_cooldowns(data):
    """Écrit de manière (quasi) atomique pour éviter la corruption."""
    tmp = COOLDOWN_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, COOLDOWN_FILE)

# ---- Intents & bot ----
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Persistance : cooldowns configurés
cooldowns = load_cooldowns()
# État volatile : derniers messages par (guild, user, channel) pour appliquer le délai
_last_msg_ts = {}  # {(guild_id, user_id, channel_id): unix_ts}

# ---- Utilitaires ----
def can_bypass(member: discord.Member) -> bool:
    # les modérateurs ayant "Gérer les messages" ne sont pas limités
    return member.guild_permissions.manage_messages

# ---- Commandes ----
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

@bot.tree.command(name="cooldown_set", description="Définir un cooldown (en secondes) pour un utilisateur")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_set(interaction: discord.Interaction, user: discord.Member, seconds: int):
    await interaction.response.defer(ephemeral=True)
    seconds = max(1, int(seconds))
    g = interaction.guild_id
    cooldowns.setdefault(g, {})[user.id] = seconds
    save_cooldowns(cooldowns)
    await interaction.followup.send(f"✅ **{seconds}s** appliqué à {user.mention}.", ephemeral=True)
    logging.info("[SET] %s -> %ss pour %s (%s)", interaction.user, seconds, user, interaction.guild.name)

@bot.tree.command(name="cooldown_remove", description="Supprimer le cooldown d'un utilisateur")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_remove(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    g = interaction.guild_id
    if user.id in cooldowns.get(g, {}):
        del cooldowns[g][user.id]
        if not cooldowns[g]:
            cooldowns.pop(g, None)
        save_cooldowns(cooldowns)
        await interaction.followup.send(f"🗑️ Cooldown supprimé pour {user.mention}.", ephemeral=True)
        logging.info("[REMOVE] %s a retiré le cooldown de %s (%s)", interaction.user, user, interaction.guild.name)
    else:
        await interaction.followup.send("ℹ️ Aucun cooldown trouvé pour cet utilisateur.", ephemeral=True)

@bot.tree.command(name="cooldown_show", description="Afficher le cooldown d'un utilisateur")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_show(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    g = interaction.guild_id
    s = cooldowns.get(g, {}).get(user.id)
    if s:
        await interaction.followup.send(f"🔎 {user.mention} a un cooldown de **{s}s**.", ephemeral=True)
    else:
        await interaction.followup.send("📭 Aucun cooldown pour cet utilisateur.", ephemeral=True)

@bot.tree.command(name="cooldown_list", description="Lister tous les cooldowns du serveur")
@app_commands.checks.has_permissions(manage_messages=True)
async def cooldown_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    g = interaction.guild_id
    data = cooldowns.get(g, {})
    if not data:
        await interaction.followup.send("📭 Aucun cooldown sur ce serveur.", ephemeral=True)
        return
    lines = [f"• <@{uid}> → {sec}s" for uid, sec in data.items()]
    await interaction.followup.send("\n".join(lines), ephemeral=True)

# ---- Application du cooldown ----
@bot.event
async def on_message(message: discord.Message):
    if not message.guild or message.author.bot:
        return

    # les modérateurs ne sont pas limités
    if can_bypass(message.author):
        return

    g = message.guild.id
    u = message.author.id
    ch = message.channel.id

    s = cooldowns.get(g, {}).get(u)  # secondes configurées
    if not s:
        return

    now = time.time()
    last = _last_msg_ts.get((g, u, ch), 0.0)

    if now - last < s:
        # encore sous cooldown → suppression du message
        try:
            await message.delete()
            remaining = int(round(s - (now - last)))
            await message.channel.send(
                f"⏳ {message.author.mention}, attends encore **{remaining}s** avant d'envoyer un nouveau message ici.",
                delete_after=5
            )
            logging.info("[CD] Suppression de %s dans #%s (%s)", message.author, message.channel.name, message.guild.name)
        except discord.Forbidden:
            logging.warning("Permission insuffisante pour supprimer/écrire dans #%s", message.channel.name)
        except Exception as e:
            logging.exception("Erreur sur suppression cooldown", exc_info=e)
        return

    _last_msg_ts[(g, u, ch)] = now
    await bot.process_commands(message)

# ---- Ready ----
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        logging.exception("Sync slash commands échouée", exc_info=e)
    logging.info("✅ Connecté en tant que %s (%s)", bot.user, bot.user.id)

# ---- Démarrage ----
keep_alive()  # no-op en Worker, utile en Web Service
bot.run(os.environ["DISCORD_TOKEN"])
