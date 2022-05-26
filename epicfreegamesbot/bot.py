import asyncio
import json
import logging
from os import path

from interactions import CommandContext, Client, Option, OptionType, Guild, Embed, Channel, ChannelType

from epicfreegamesbot.permissions import Permissions, has_permission
from epicfreegamesbot.util import get_free_games, get_game_embeds


class EpicFreeGamesBot(Client):
    def __init__(self, config_file, **kwargs):
        if not path.isfile(config_file):
            raise ValueError('Config file is not accessible')
        with open(config_file) as f:
            self.config = json.load(f)
        super(EpicFreeGamesBot, self).__init__(token=self.config['bot_token'], **kwargs)
        self.config_file = config_file
        self.free_games = []
        self.logger = logging.getLogger('EpicFreeGamesBot')

        # noinspection PyTypeChecker
        self.event(self.on_ready, 'on_ready')
        # noinspection PyTypeChecker
        self.event(self.on_guild_join, 'on_guild_join')

        self.command(
            name='set-game-channel',
            description='Sets the channel to send new free game announcements into',
            options=[Option(
                name='channel',
                description='The channel to send new free games in',
                type=OptionType.CHANNEL,
                required=True
            )]
        )(self.set_game_channel)

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.me.name}')
        guild_list = self._http.cache.guilds.values.values()
        self.logger.info(f'The bot is on {len(guild_list)} servers')
        for guild in guild_list:
            self.logger.info(f'- {guild.name} ({guild.id})')
        self.logger.info('on_ready done, starting loop')
        while True:
            await self.check_and_update_games()
            await asyncio.sleep(600)

    async def on_guild_join(self, guild: Guild):
        self.logger.info(f'Joined guild {guild.name}')
        if str(guild.id) not in self.config:
            self.config[str(guild.id)] = {}

    async def set_game_channel(self, ctx: CommandContext, channel: Channel):
        await ctx.defer(True)
        self.logger.info(f'{ctx.author.user.username} ran command set-game-channel')
        guild = Guild(**await self._http.get_guild(ctx.guild_id))

        # Make sure the user actually supplied a text channel
        if channel.type not in (ChannelType.GUILD_TEXT, ChannelType.GUILD_NEWS):
            await ctx.send(
                content='This channel is not a text channel',
                ephemeral=True
            )
            return
        # Make sure the user is allowed to use the command (has "Manage Messages" perm)
        if not has_permission(int(ctx.author.permissions), Permissions.MANAGE_MESSAGES):
            await ctx.send(
                content='You do not have permission to use this command',
                ephemeral=True
            )
            return
        if str(guild.id) not in self.config:
            self.config[str(guild.id)] = {}
        # If we didn't have an announcement channel set before, announce the current free games in the newly set channel
        if 'announcementChannel' not in self.config[str(ctx.guild_id)]:
            self.config[str(ctx.guild_id)]['announcementChannel'] = int(channel.id)
            self.update_free_games()
            await self.send_game_announcements(get_game_embeds(self.free_games), guild)
        else:
            self.config[str(ctx.guild_id)]['announcementChannel'] = int(channel.id)
        self.sync_config()
        await ctx.send(
            content=f'Set the game announcement channel to <#{channel.id}>',
            ephemeral=True
        )

    def sync_config(self):
        self.logger.info('Saving config...')
        # Try to dump the config first before writing to file
        # This ensures that the config isn't corrupted when something isn't serializable
        try:
            json.dumps(self.config, indent=4, sort_keys=True)
        except TypeError:
            from pprint import pprint
            self.logger.critical(
                'Unable to save config! Please restart the bot ASAP, no new data will be saved to disk!'
            )
            self.logger.info('Non-savable config in dict format:')
            pprint(self.config)
            return
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4, sort_keys=True)

    async def check_and_update_games(self):
        self.update_free_games()
        embed_list = get_game_embeds(self.free_games)
        guilds = [Guild(**x) for x in await self._http.get_self_guilds()]
        # Uncomment to test on just one guild
        # guilds = [Guild(** await self.http.get_guild(guild_id_here))]
        for guild in guilds:
            try:
                await self.send_game_announcements(embed_list, guild)
            except Exception as e:
                self.logger.error(f'Got {e} when sending game announcements to {guild.name}, ignoring')
            else:
                self.sync_config()

    async def send_game_announcements(self, game_embed_dict: dict, guild: Guild):
        if str(guild.id) not in self.config:
            self.config[str(guild.id)] = {}
        # Can't announce games without an announcement channel
        if 'announcementChannel' not in self.config[str(guild.id)]:
            return

        try:
            channel_to_send: Channel = Channel(
                **await self._http.get_channel(self.config[str(guild.id)]['announcementChannel'])
            )
        except ValueError:
            self.logger.error(f'Got ValueError when fetching channel for {guild.name}, does it still exist?')
            return
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
                # noinspection PyProtectedMember
                await self._http.send_message(channel_to_send.id, '', embeds=[embed._json])
            # In case we can't send the message, log it
            # For instance, the channel could no longer exist, or the bot could not have access to it
            except Exception as e:
                self.logger.error(f'Unable to send message into #{channel_to_send.name}: {e}')
                continue
            # If the announcement worked, store and log it
            self.logger.info(f'Sent free game {embed.title} into #{channel_to_send.name} on server {guild.name}')
            self.config[str(guild.id)]['announcedGames'].append(game_slug)

    def update_free_games(self):
        free_games = get_free_games()
        # If we don't have free game data, we can't update anything
        if not free_games:
            return
        # If the free games haven't changed, don't do anything
        if free_games == self.free_games:
            return
        self.logger.info(f'Updated game list ({len(free_games)} game(s))')
        self.free_games = free_games
