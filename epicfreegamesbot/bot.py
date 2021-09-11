import asyncio
import json
import logging
from json import load
from os import path

from discord import TextChannel, Guild, Embed
from discord.ext.commands import Bot
from discord_slash.context import InteractionContext
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option

from epicfreegamesbot.util import get_free_games, get_game_embeds


class EpicFreeGamesBot(Bot):
    def __init__(self, config_file, command_prefix='!', **options):
        super(EpicFreeGamesBot, self).__init__(command_prefix, **options)
        self.slash_handler = SlashCommand(self)
        self.config_file = config_file
        self.free_games = []
        self.logger = logging.getLogger('EpicFreeGamesBot')
        if not path.isfile(config_file):
            raise ValueError('Config file is not accessible')
        with open(config_file) as f:
            self.config = load(f)

    async def on_ready(self):
        await self.sync_commands()
        self.logger.info('Logged in as {}'.format(self.user))
        self.logger.info('The bot is on {} servers'.format(len(self.guilds)))
        guild: Guild
        for guild in self.guilds:
            self.logger.info('- {} ({})'.format(guild.name, guild.id))
        self.logger.info('on_ready done, starting loop')
        while True:
            await self.check_and_update_games()
            await asyncio.sleep(600)

    async def on_guild_join(self, guild: Guild):
        self.logger.info('Joined guild {}'.format(guild.name))
        if str(guild.id) not in self.config:
            self.config[str(guild.id)] = {}
        await self.sync_commands()

    async def sync_commands(self):
        self.slash_handler.add_slash_command(
            cmd=self.set_game_channel,
            name='set-game-channel',
            description='Set the channel to send new free game announcements into',
            guild_ids=list(guild.id for guild in self.guilds),
            options=[
                create_option(
                    name="channel",
                    description='The channel to send new free games in',
                    option_type=7,
                    required=True
                )
            ]
        )
        await self.slash_handler.sync_all_commands()

    async def set_game_channel(self, ctx: InteractionContext, channel: TextChannel):
        self.logger.info('{} ran command in {}'.format(ctx.author.name, ctx.guild.name))
        # Make sure the user actually supplied a text channel
        if not isinstance(channel, TextChannel):
            await ctx.send(
                content='This channel is not a text channel',
                hidden=True
            )
            return
        # Make sure the user is allowed to use the command (has "Manage Messages" perm)
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                content='You do not have permission to use this command',
                hidden=True
            )
            return
        # If we didn't have an announcement channel set before, announce the current free games in the newly set channel
        if 'announcementChannel' not in self.config[str(ctx.guild_id)]:
            self.config[str(ctx.guild_id)]['announcementChannel'] = channel.id
            self.update_free_games()
            await self.send_game_announcements(get_game_embeds(self.free_games), ctx.guild)
        else:
            self.config[str(ctx.guild_id)]['announcementChannel'] = channel.id
        self.sync_config()
        await ctx.send(
            content='Set the game announcement channel to <#{}>'.format(channel.id),
            hidden=True
        )

    def sync_config(self):
        self.logger.info('Saving config...')
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4, sort_keys=True)

    async def check_and_update_games(self):
        self.update_free_games()
        embed_list = get_game_embeds(self.free_games)
        for guild in self.guilds:
            await self.send_game_announcements(embed_list, guild)
        self.sync_config()

    async def send_game_announcements(self, game_embed_dict: dict, guild: Guild):
        # Can't announce games without an announcement channel
        if 'announcementChannel' not in self.config[str(guild.id)]:
            return

        channel_to_send: TextChannel = self.get_channel(self.config[str(guild.id)]['announcementChannel'])
        game_slug: str
        embed: Embed
        for game_slug, embed in game_embed_dict.items():
            # Make sure we have a list of already announced games
            if 'announcedGames' not in self.config[str(guild.id)]:
                self.config[str(guild.id)]['announcedGames'] = []
            # If we already announced this game, skip it
            if game_slug in self.config[str(guild.id)]['announcedGames']:
                continue

            # Try to send them message
            try:
                await channel_to_send.send(embed=embed)
            # In case we can't send the message, log it
            # For instance, the channel could no longer exist, or the bot could not have access to it
            except Exception as e:
                self.logger.error('Unable to send message into #{}: {}'.format(channel_to_send.name, e))
                continue
            # If the announcement worked, store and log it
            self.logger.info('Sent free game {} into #{} on server {}'.format(
                embed.title, channel_to_send.name, channel_to_send.guild.name
            ))
            self.config[str(guild.id)]['announcedGames'].append(game_slug)

    def update_free_games(self):
        free_games = get_free_games()
        # If we don't have free game data, we can't update anything
        if not free_games:
            return
        # If the free games haven't changed, don't do anything
        if free_games == self.free_games:
            return
        self.logger.info('Updated game list ({} games)'.format(len(free_games)))
        self.free_games = free_games
