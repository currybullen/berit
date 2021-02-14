import sys
import requests
import re
import discord
import logging
import argparse
import os
import random

DATA_SOURCES_METADATA = "https://api.scryfall.com/bulk-data/oracle-cards"


def main(args):
    cards = fetch_cards_from_source()
    start_discord_listener(cards, args.token, args.channel)


def fetch_cards_from_source():
    oracle_source = requests.get(DATA_SOURCES_METADATA).json()["download_uri"]
    oracle_data = requests.get(oracle_source).json()

    def valid_card(card):
        return (card["object"] == "card"
                and card["lang"] == "en"
                and card["legalities"]["commander"] == "legal")

    def sort_key(card):
        return re.match("Legendary.*Creature", card["type_line"]) is None

    def trim_card(card):
        return {"commander": bool(re.match("Legendary.*Creature", card["type_line"])),
                "scryfall_uri": card["scryfall_uri"]}

    cards = sorted(filter(valid_card, oracle_data), key=sort_key)
    return {card["name"].lower(): trim_card(card) for card in cards}


def find_card(pattern, cards):
    pattern = pattern.lower()

    if pattern == "!random":
        return list(cards.values())[random.randint(0, len(cards) - 1)]

    if pattern == "!random_commander":
        commanders = filter(lambda card: card["commander"], list(cards.values()))
        commanders = list(commanders)
        return commanders[random.randint(0, len(commanders) - 1)]

    if cards.get(pattern):
        return cards[pattern]

    return next(
        map(lambda name: cards[name],
            filter(lambda name: pattern in name, cards.keys())),
        None)


def start_discord_listener(cards, token, subscribed_channels):
    client = discord.Client()

    @client.event
    async def on_ready():
        logging.info(f"Logged in as {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            logging.debug(f"Ignoring message sent by myself.")
            return

        if str(message.channel) not in subscribed_channels:
            logging.debug(f"Ignoring message sent in channel other than {subscribed_channels}.")
            return

        patterns = re.findall("\[(.+?)\]", message.content)
        if not patterns:
            logging.debug(f"No patterns could be extracted from message '{message.content}'.")
            return

        matches = list(filter(None, map(lambda pattern: find_card(pattern, cards), patterns)))
        if not matches:
            logging.debug(f"No card(s) found matching patterns '{patterns}'.")
            return

        result = [card.get("scryfall_uri") for card in matches]
        logging.info(f"Returning cards '{result}' matching patterns '{patterns}'.")
        formatted_result = "\n".join(result)
        await message.channel.send(f"{formatted_result}")

    client.run(token)


def parse_args():
    parser = argparse.ArgumentParser(description="A Discord MTG bot ")
    parser.add_argument("--token",
                        help="Relevant Discord bot token.",
                        default=os.environ.get("BERIT_TOKEN"))
    parser.add_argument("--channel",
                        action="append",
                        help="A channel which Berit listens in. May be supplied multiple times.",
                        required=True)

    args = parser.parse_args()
    if args.token is None:
        logging.error("API supplied neither by --token or env variable BERIT_TOKEN")
        sys.exit(1)

    return args


if __name__ == "__main__":
    main(parse_args())
