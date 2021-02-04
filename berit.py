import sys
import requests
import re
import discord
import logging

BULK_DATA_METADATA = "https://api.scryfall.com/bulk-data"
SUBSCRIBED_CHANNELS = ["magic"]


def main(api_key):
    cards = fetch_cards_from_source()
    start_discord_listener(cards, api_key)


def fetch_cards_from_source():
    bulk_data_sources = requests.get(BULK_DATA_METADATA).json()["data"]
    oracle_source = next(filter(lambda source: source["name"] == "Oracle Cards", bulk_data_sources))
    oracle_data = requests.get(oracle_source["download_uri"]).json()

    return {card["name"].lower(): card for card in filter(valid_card, oracle_data)}


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
    if cards.get(pattern) is not None:
        return cards[pattern]

    match = None
    legendary_creature_matched = False
    for name in cards.keys():
        if (match is None or not legendary_creature_matched) and pattern in name:
            match = cards[name]
            legendary_creature_matched = re.match("Legendary.*Creature", cards[name]["type_line"])

    return match


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

        patterns = re.findall("\[(.+?)\]", message.content)
        if not patterns:
            logging.debug(f"No patterns could be extracted from message '{message.content}'.")
            return

        matches = []
        for pattern in patterns:
            match = find_card(cards, pattern)
            if match is not None:
                matches.append(match)

        if not matches:
            logging.debug(f"No card(s) found matching patterns '{patterns}'.")
            return

        result = [card.get("scryfall_uri") for card in matches]
        logging.info(f"Returning cards '{result}' matching patterns '{patterns}'.")
        formatted_result = "\n".join(result)
        await message.channel.send(f"{formatted_result}")

    client.run(api_key)


if __name__ == "__main__":
    api_key_arg = str(sys.argv[1])
    main(api_key_arg)
