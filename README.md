# NearlyOnTime

A Discord bot for the NearlyOnRed Discord server.
It announces new anime episodes and events on Th8as website.

## Table of Contents
- [Usage](#usage)
- [Installation](#installation)
- [Running](#running)
- [Project Structure](#project-structure)

## Usage
To use the bot, mention it with your command.

```@NearlyOnTime help```

In direct messages the mention is optional.

Use the `help` command to list available commands, or `_help` to list all commands, even hidden ones.

## Installation
This bot requires Python 3.6+, as well as the following dependencies:
	[`discord.py`](https://pypi.org/project/discord.py/)

Optionally, you can install [`cchardet`](https://pypi.org/project/cchardet/) and [`aiodns`](https://pypi.org/project/aiodns/) to improve performance.
```sh
# Install dependencies
# Note: You might need to use 'sudo -H' to get proper permission
$ python3 -m pip install -U discord.py
$ python3 -m pip install -U cchardet aiodns

# Clone repo
$ git clone https://github.com/max-kamps/nearly-on-time.git nearly_on_time

# Create the credentials file
$ cd nearly_on_time
$ cp credentials.example.json credentials.hjson

# Make sure to edit the credentials file
# You can add multiple named tokens for testing purposes if you want to

# Running
$ cd ..
$ python3 -m nearly_on_time main
```

## Running
```sh
$ python3 -m nearly_on_time <account>
```
