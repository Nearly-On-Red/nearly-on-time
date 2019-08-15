# NearlyOnTime

A Discord bot for the NearlyOnRed Discord server.
It announces new anime episodes and events on Th8as website.

## Usage
To use the bot, mention it with your command.

```@NearlyOnTime help```

In direct messages the mention is optional.

Use the `help` command to list available commands, or `_help` to list all commands, even hidden ones.

## Installation
This bot requires Python 3.6+, as well as the following dependencies:
	[`discord.py`](https://pypi.org/project/discord.py/)
	[`hjson`](https://pypi.org/project/hjson/)
	[`feedparser`](https://pypi.org/project/feedparser/)

Optionally, you can install [`cchardet`](https://pypi.org/project/cchardet/) and [`aiodns`](https://pypi.org/project/aiodns/) to improve performance.
```sh
# Install dependencies
# Note: You might need to use 'sudo -H' to get proper permission
$ python3 -m pip install -U discord.py hjson feedparser
$ python3 -m pip install -U cchardet aiodns

# Clone repo
$ git clone https://github.com/max-kamps/nearly-on-time.git nearly_on_time

# Create the config file
$ cd nearly-on-time
$ cp example.config.hjson config.hjson

# Make sure to edit your config file
# You can add multiple named tokens for testing purposes if you want to

# Running
$ cd ..
$ python3 -m nearly_on_time main
```

## Running
```sh
$ python3 -m nearly_on_time <account>
```
