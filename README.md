# EpicFreeGamesBot
A Discord bot that announces the free games of the Epic Games Store

## Setup
Either add [my public instance](https://discord.com/api/oauth2/authorize?client_id=780207406579318784&permissions=2048&scope=bot%20applications.commands) of the bot to your server or host the bot yourself and invite it.  
Once you have the bot added, run `/set-game-channel` and provide the channel the bot's supposed to send messages into

## Issues
Currently, [interactions.py](https://github.com/interactions-py/library) (a library I'm using) does not offer reconnection logic. Because of this, the bot may crash after a few hours of running. This also happens to my own instance.  
If you're self-hosting, you can restart the bot yourself. If you're using my instance, you can [contact me on Discord](https://discord.gg/AnpecXfHrn) and I'll start it back up for you.

## Self-Hosting
 - Install `requests` and `discord-py-interactions` using pip
 - `git clone` this Repo
 - Rename "sample_config.json" to "config.json" and paste in your Bot token
 - Run `PYTHONPATH=. python main.py`
