import sys
import requests
import re
import discord
import logging
import argparse
import os

SEARCH_ENDPOINT = "https://api.scryfall.com/cards/search"
RANDOM_ENDPOINT = "https://api.scryfall.com/cards/random"

# TODO: Wrap lines here maybe
HELP_TEXT = """
    Berit listens to the following commands:

    [<search term>]:

    Find the EDH legal card matching <search term> with the highest EDHREC score. Consult the full search reference at https://scryfall.com/docs/syntax.

    [!random_commander]:

    Find a random EDH legal commander.

    [!random_rare]:

    Find a random EDH legal card with rarity rare or rarer.

    [!help]:

    Print this text
    """


def main(args):
    start_discord_listener(args.token, args.channel)


def run_commands(commands: str) -> List[str]:
    if "!help" in commands:
        return [HELP_TEXT]
    else:
        return list(filter(None, [run_command(command) for command in commands]))


def run_command(command: str) -> str:
    match command.lower():
        case "!random_rare":
            return requests.get(RANDOM_ENDPOINT, params={"q": "format:commander rarity>=rare"}).json()["scryfall_uri"]
        case "!random_commander":
            return requests.get(RANDOM_ENDPOINT, params={"q": "is:commander"}).json()["scryfall_uri"]
        case _:
            return find_card(command)



def find_card(pattern: str) -> str:
    payload = {
        "q": f"{pattern}",
        "order": "edhrec"
    }
    result = requests.get(SEARCH_ENDPOINT, params=payload).json()

    if result["object"] != "list":
        logging.debug(f"No cards found when requesting with parameters {payload}")
        return None

    return result["data"][0]["scryfall_uri"]


def start_discord_listener(token: str, subscribed_channels: list[str]):
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

        outputs = run_commands(commands)
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
        logging.error("Bot token supplied neither by --token or env variable BERIT_TOKEN")
        sys.exit(1)

    return args


if __name__ == "__main__":
    main(parse_args())
