import sys
import requests
import re
import discord
import logging
import argparse
import os

DATA_SOURCES_METADATA = "https://api.scryfall.com/bulk-data"
SUBSCRIBED_CHANNELS = ["magic"]


def main(args):
    cards = fetch_cards_from_source()
    start_discord_listener(cards, args.api_key, args.channel)


def fetch_cards_from_source():
    data_sources = requests.get(DATA_SOURCES_METADATA).json()["data"]
    oracle_source = next(filter(lambda source: source["name"] == "Oracle Cards", data_sources))
    oracle_data = requests.get(oracle_source["download_uri"]).json()

    def valid_card(card):
        return (card["object"] == "card"
                and card["lang"] == "en"
                and card["legalities"]["commander"] == "legal")

    def sort_key(card):
        return re.match("Legendary.*Creature", card["type_line"]) is None

    cards = sorted(filter(valid_card, oracle_data), key=sort_key)
    return {card["name"].lower(): card for card in cards}


def find_card(pattern, cards):
    pattern = pattern.lower()

    if cards.get(pattern):
        return cards[pattern]

    return next(
        map(lambda name: cards[name],
            filter(lambda name: pattern in name, cards.keys())),
        None)


def start_discord_listener(cards, api_key, subscribed_channels):
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
            logging.debug(f"Ignoring message sent in channel other than {SUBSCRIBED_CHANNELS}.")
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

    client.run(api_key)


def parse_args():
    parser = argparse.ArgumentParser(description="A Discord MTG bot ")
    parser.add_argument("--api-key",
                        help="Relevant Discord API key.",
                        default=os.environ.get("BERIT_API_KEY"))
    parser.add_argument("--channel",
                        action="append",
                        help="A channel which Berit listens in. May be supplied multiple times.",
                        required=True)

    args = parser.parse_args()
    if args.api_key is None:
        logging.error("API supplied neither by --api-key or env variable BERIT_API_KEY.")
        sys.exit(1)

    return args


if __name__ == "__main__":
    main(parse_args())
