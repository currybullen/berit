import argparse
import sys
import requests
import re
import discord
import logging

BULK_DATA_METADATA = "https://api.scryfall.com/bulk-data"
SUBSCRIBED_CHANNELS = ["magic"]


def main(api_key):
    logging.basicConfig(level=logging.DEBUG)
    cards = fetch_cards_from_source()
    start_discord_listener(cards, api_key)


def fetch_cards_from_source():
    bulk_data_sources = requests.get(BULK_DATA_METADATA).json()["data"]
    oracle_data_uri = None
    for source in bulk_data_sources:
        if source["name"] == "Oracle Cards":
            oracle_data_uri = source["download_uri"]

    cards = {}
    for card in requests.get(oracle_data_uri).json():
        if valid_card(card):
            cards[card["name"].lower()] = card
    return cards


def valid_card(card):
    if card["object"] != "card":
        return False
    if card["lang"] != "en":
        return False
    if card["legalities"]["commander"] != "legal":
        return False
    return True


def find_card(cards, pattern):
    pattern = pattern.lower()
    any_match = None
    for name in cards.keys():
        if name == pattern:
            return cards[name]
        if any_match is None and re.search(pattern, name, flags=re.IGNORECASE):
            any_match = cards[name]

    return any_match


def start_discord_listener(cards, api_key):
    client = discord.Client()

    @client.event
    async def on_ready():
        logging.info(f"Logged in as {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            logging.debug(f"Ignoring message sent by myself.")
            return

        if str(message.channel) not in SUBSCRIBED_CHANNELS:
            logging.debug(f"Ignoring message sent in channel other than {SUBSCRIBED_CHANNELS}.")
            return

        pattern = re.match("^\[(.+)\]$", message.content).group(1)
        if pattern is None:
            logging.debug(f"No pattern could be extracted from message '{message.content}'.")
            return

        card = find_card(cards, pattern)
        if card is None:
            logging.debug(f"No card found matching pattern '{pattern}'.")
            return

        scryfall_uri = card["scryfall_uri"]
        logging.info(f"Returning card '{scryfall_uri}' matching pattern '{pattern}'.")
        await message.channel.send(f"{scryfall_uri}")

    client.run(api_key)


if __name__ == "__main__":
    api_key_arg = str(sys.argv[1])
    main(api_key_arg)
