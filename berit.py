import sys
import requests
import re
import discord
import logging

DATA_SOURCES_METADATA = "https://api.scryfall.com/bulk-data"
SUBSCRIBED_CHANNELS = ["magic"]


def main(api_key):
    commanders, other_99 = fetch_cards_from_source()
    start_discord_listener(commanders, other_99, api_key)


def fetch_cards_from_source():
    data_sources = requests.get(DATA_SOURCES_METADATA).json()["data"]
    oracle_source = next(filter(lambda source: source["name"] == "Oracle Cards", data_sources))
    oracle_data = requests.get(oracle_source["download_uri"]).json()

    def valid_card(card):
        return (card["object"] == "card"
                and card["lang"] == "en"
                and card["legalities"]["commander"] == "legal")

    commanders = {}
    other_99 = {}
    for card in filter(valid_card, oracle_data):
        if re.match("Legendary.*Creature", card["type_line"]):
            commanders[card["name"].lower()] = card
        else:
            other_99[card["name"].lower()] = card

    return commanders, other_99


def find_card(commanders, other_99, pattern):
    pattern = pattern.lower()

    if commanders.get(pattern):
        return commanders[pattern]
    if other_99.get(pattern):
        return other_99[pattern]

    for name in commanders.keys():
        if pattern in name:
            return commanders[name]
    for name in other_99.keys():
        if pattern in name:
            return other_99[name]

    return None


def start_discord_listener(commanders, other_99, api_key):
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
            match = find_card(commanders, other_99, pattern)
            if match:
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
