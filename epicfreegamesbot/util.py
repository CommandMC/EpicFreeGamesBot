import datetime
import logging

from discord import Embed
from discord.embeds import EmptyEmbed
from requests import get, ConnectionError


def get_free_games() -> list[dict]:
    try:
        res = get('https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions')
    except ConnectionError:
        return []
    if not res.ok:
        return []

    try:
        free_games = res.json()['data']['Catalog']['searchStore']['elements']
    except TypeError:
        return []
    final_free_game_list = []
    for game in free_games:
        # Epic sometimes leaves games that were previously free on that site.
        # These games then have no actual promotion data, so filter them out that way
        if not game['promotions']:
            continue
        # Only show games that are currently free
        if not game['promotions']['promotionalOffers']:
            continue

        promotional_offers = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]
        # Just in case: Check if the end date is still in the future
        # Epic hasn't messed this up yet, but I'd say it's only a matter of time
        end_date = promotional_offers['endDate']
        end_date = datetime.datetime.fromisoformat(end_date[:-1])
        if not end_date > datetime.datetime.now():
            continue

        # Make sure the game is actually free and not just discounted
        if promotional_offers['discountSetting']['discountPercentage'] != 0:
            continue

        final_free_game_list.append(game)
    return final_free_game_list


def get_game_embeds(games: list[dict]):
    logger = logging.getLogger('GameEmbeds')
    embed_list: dict[Embed] = {}
    for game in games:
        start_time = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['startDate']
        start_time = datetime.datetime.fromisoformat(start_time[:-1])
        url = 'https://www.epicgames.com/store/en-US/p/' + game['productSlug'].replace('--', '/')
        # Since Epic is great, sometimes 'productSlug' works for the URL, and sometimes 'urlSlug' does
        # Check if product is giving a 404, use url if it does
        if 'error-404' in get(url).url:
            logger.info('productSlug did not work, trying urlSlug instead')
            url = 'https://www.epicgames.com/store/en-US/p/' + game['urlSlug'].replace('--', '/')
            # If both url and product don't work, just don't give a URL (this shouldn't ever happen)
            if 'error-404' in get(url).url:
                logger.info('urlSlug also did not work, not supplying URL')
                url = EmptyEmbed

        embed = Embed(
            title=game['title'],
            description=game['description'],
            url=url,
            timestamp=start_time
        )
        embed.set_footer(text='New free game')
        embed.set_thumbnail(
            url=next(link['url'].replace(' ', '%20') for link in game['keyImages'] if link['type'] == 'Thumbnail')
        )
        embed_list[game['productSlug']] = embed
    return embed_list
