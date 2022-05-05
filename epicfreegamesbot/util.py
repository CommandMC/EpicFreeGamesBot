import datetime
import logging

from interactions import Embed, EmbedFooter, EmbedImageStruct
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
        if not end_date > datetime.datetime.utcnow():
            continue

        # Make sure the game is actually free and not just discounted
        if promotional_offers['discountSetting']['discountPercentage'] != 0:
            continue

        final_free_game_list.append(game)
    return final_free_game_list


# noinspection PyProtectedMember
def get_game_embeds(games: list[dict]):
    logger = logging.getLogger('GameEmbeds')
    embed_list: dict[Embed] = {}
    for game in games:
        start_time = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['startDate'][:-1]

        # Make sure the game has a productSlug and that it's not empty
        if 'productSlug' not in game or not game['productSlug']:
            game['productSlug'] = game['urlSlug']

        url = ''
        if game['offerMappings']:
            for mapping in game['offerMappings']:
                if mapping['pageType'] == 'productHome':
                    url = 'https://www.epicgames.com/store/en-US/p/' + mapping['pageSlug']
                    break

        if not url:
            logger.info('Unable to get URL from offerMappings, setting generic URL')
            url = 'https://www.epicgames.com/store/en-US/free-games'

        embed_footer = EmbedFooter(text='New free game')._json
        embed_thumbnail = EmbedImageStruct(url=next(
            link['url'].replace(' ', '%20')
            for link in game['keyImages']
            if link['type'] in ('Thumbnail', 'DieselStoreFrontWide')
        ))._json
        embed = Embed(
            title=game['title'],
            description=game['description'],
            url=url,
            timestamp=start_time,
            footer=embed_footer,
            thumbnail=embed_thumbnail
        )
        embed_list[game['productSlug']] = embed
    return embed_list


def main():
    free_games = get_free_games()
    embeds = get_game_embeds(free_games)
    print(embeds)
    for game_slug, embed in embeds.items():
        print(game_slug)
        print(embed.url)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s/%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    main()
