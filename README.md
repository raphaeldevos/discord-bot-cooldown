# Discord Bot — Déploiement Railway (gratuit)

Repo prêt à l'emploi pour héberger un **bot Discord officiel** sur **Railway.app**.

## Fichiers inclus
- `cooldown_bot.py` — bot minimal (prefix `!`, commande `!ping` avec cooldown)
- `requirements.txt` — dépendances Python
- `Procfile` — définit un **worker** pour Railway (pas d'app web)
- `.env.example` — exemple de variables d'environnement (pour tests locaux)

## Déploiement sur Railway (étapes rapides)
1. **Fork/Upload** ce dossier sur **GitHub**.
2. Sur **Railway → New Project → Deploy from GitHub repo** et sélectionne ce repo.
3. Dans **Variables**, ajoute :
   - `DISCORD_TOKEN` = *ton token de bot* (depuis Discord Developer Portal).
4. Le build s'exécute puis le bot démarre automatiquement. Regarde **Logs** pour voir `Connecté en tant que ...`.

### Remarques
- **Aucun userbot** : ceci est pour un bot officiel (conforme aux règles Discord).
- Si tu veux d'autres commandes, ajoute-les dans `cooldown_bot.py`.
- Si tu as besoin des *slash commands*, on peut ajouter un `app_commands.CommandTree` ensuite.
