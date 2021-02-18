import sys
import requests
import re
import discord
import logging
import argparse
import os
import random

DATA_SOURCES_METADATA = "https://api.scryfall.com/bulk-data/oracle-cards"
HELP_TEXT = """
    Berit listens to the following commands:

    [<substring>]: Find the first EDH legal card matching <substring>. Legendary creatures are prioritized.
    [!random_commander]: Find a random EDH legal commander.
    [!random_rare]: Find a random EDH legal rare.
    [!help]: Print this text
    """


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

    def sort_by_type(card):
        return re.match("Legendary.*Creature", card["type_line"]) is None

    cards = sorted(filter(valid_card, oracle_data), key=sort_by_type)

    def trim_card(card):
        return {"commander": bool(re.match("Legendary.*Creature", card["type_line"])),
                "scryfall_uri": card["scryfall_uri"]}

    return {card["name"].lower(): trim_card(card) for card in cards}


def run_commands(commands, cards):
    if "!help" in commands:
        return [HELP_TEXT]
    else:
        return list(filter(None, [run_command(command, cards) for command in commands]))


def run_command(command, cards):
    if command == "!random":
        return list(cards.values())[random.randint(0, len(cards) - 1)]["scryfall_uri"]

    if command == "!random_commander":
        commanders = filter(lambda card: card["commander"], list(cards.values()))
        commanders = list(commanders)
        return commanders[random.randint(0, len(commanders) - 1)]["scryfall_uri"]

    return find_card(command, cards)


def find_card(pattern, cards):
    if cards.get(pattern):
        return cards[pattern]["scryfall_uri"]

    result = next(
        map(lambda name: cards[name]["scryfall_uri"],
            filter(lambda name: pattern in name, cards.keys())),
        None)

    if result is None:
        logging.debug(f"No card(s) found matching pattern '{pattern}'.")

    return result


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

        commands = re.findall("\[(.+?)\]", message.content)
        if not commands:
            logging.debug(f"No commands could be extracted from message '{message.content}'.")
            return

        commands = [command.lower() for command in commands]
        outputs = run_commands(commands, cards)
        if not outputs:
            return

        formatted_output = "\n".join(outputs)
        await message.channel.send(f"{formatted_output}")

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
