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

## Project Structure
- `__main__.py`: This is the entry point of the application. The config file is loaded here, the correct token is selected and the bot class is instantiated.
- `bot.py`: This file contains the actual bot class (`NearlyOnTime`), as well as the `eval`, `exec` and `times` commands.
- `module.py`: Module loading is implemented here. In the future, this will also manage the configuration data of the modules.
- Most actual functionality is located in the `modules` folder
    - `_example.py` can be used as a template if you want to add a new module.
    - `help.py` contains the `help` and `_help` commands
    - `modutil.py` contains the `modules`, `modules load` and `modules unload` commands
    - `airing.py` is responsible for posting announcements when a new episode airs. It currently pulls some information from `Livechart` and some from `Anilist`.
    - `events.py` posts announcements when an event from `www.nearlyonred.com/events/` is about to start.
    It is currently non-functional while Th8a works on the website.
- `common.py` includes some utility functions used in multiple places
- `mixins.py` adds additional methods to some classes in the discord library.
