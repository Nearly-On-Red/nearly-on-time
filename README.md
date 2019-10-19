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
* [`discord.py`](https://pypi.org/project/discord.py/)

Optionally, you can install [`cchardet`](https://pypi.org/project/cchardet/) and [`aiodns`](https://pypi.org/project/aiodns/) to improve performance.

This is the recommended installation for Linux servers.
We will create a new user for the bot, place all the code in that users home directory and then create a systemd user service to run the bot.
```sh
# Install dependencies
$ sudo -H python3 -m pip install -U discord.py cchardet aiodns

# Create new user
$ sudo useradd -m nearlybot
$ sudo passwd -l nearlybot
$ sudo loginctl enable-linger nearlybot
$ sudo su nearlybot
$ cd ~

# Clone repo
$ git clone https://github.com/max-kamps/nearly-on-time.git nearly_on_time

# Create the credentials file
$ cd nearly_on_time
$ cp credentials.example.json credentials.json

# Make sure to edit the credentials file
# You can add multiple named tokens to run multiple instances of the bot if you want to

# Create the user service
$ mkdir -p ~/.config/systemd/user
$ ln -s ~/nearly_on_time/nearlybot@.service ~/.config/systemd/user/nearlybot@.service
$ export XDG_RUNTIME_DIR=/run/user/`id -u`  # Work around some weird XDG issues

# Replace main with any token name you want to run
$ systemctl --user enable nearlybot@main
$ systemctl --user start nearlybot@main

# We're done, exit su
$ exit
```

Alternatively, you can install the bot without creating a service.
Note that this means you will have to manually restart the bot if it crashes.
This is the recommended installation if you want to develop the bot.
```sh
# Install dependencies
$ sudo -H python3 -m pip install -U discord.py cchardet aiodns

# Clone repo
$ git clone https://github.com/max-kamps/nearly-on-time.git nearly_on_time

# Create the credentials file
$ cd nearly_on_time
$ cp credentials.example.json credentials.json

# Make sure to edit the credentials file
# You can add multiple named tokens to run multiple instances of the bot if you want to

$ cd ..

# Now we can run the bot!
# Replace main with any token name you want to run
$ python3 -m nearly_on_time main
```
