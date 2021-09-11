import logging
from epicfreegamesbot.bot import EpicFreeGamesBot


def main():
    bot = EpicFreeGamesBot('config.json')
    bot.run(bot.config['bot_token'])


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s/%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    main()
