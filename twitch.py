# The magical single-file Twitch API wrapper
# Now with extra leaky abstractions!

# You're probably asking yourself "Why?"
# Don't worry, I am too.

import asyncio
import json
import logging
import re
import time
from collections import namedtuple

import aiohttp
from discord.backoff import ExponentialBackoff

from gs6ex.common import Obj


irc_log = logging.getLogger('twitch.irc')
pubsub_log = logging.getLogger('twitch.pubsub')


# IRC message parsing

IRCMessage = namedtuple('IRCMessage', 'tags name nick host command params')

def try_index(string, *args):
    try:
        return string.index(*args)
    except ValueError:
        return None


escape_re = re.compile(r'\\([rns:\\])')
escape_values = {
    'r': '\r', 'n': '\n', 's': ' ',
    ':': ';', '\\': '\\'
}
escape_repl = lambda m: escape_values[m[1]]


def parse_irc_message(string):
    string = string.strip()
    pos = 0
    tags = {}
    nick = None
    name = None
    host = None

    if string[pos] == '@':
        pos += 1
        last_end = string.index(' ', pos)

        while pos < last_end:
            equals = string.index('=', pos)
            end = try_index(string, ';', equals + 1, last_end) or last_end

            key = string[pos:equals]
            value = string[equals + 1:end]
            tags[key] = escape_re.sub(escape_repl, value)

            pos = end + 1

        while string[pos] == ' ':
            pos += 1

    if string[pos] == ':':
        pos += 1
        prefix_end = string.index(' ', pos)
        prefix = string[pos:prefix_end]

        if '!' in prefix:
            nick, rest = prefix.split('!', maxsplit=1)

            name, host = rest.split('@', maxsplit=1)
        else:
            host = prefix

        pos = prefix_end

        while string[pos] == ' ':
            pos += 1

    command_end = string.index(' ', pos)
    command = string[pos:command_end]
    pos = command_end
    
    while string[pos] == ' ':
        pos += 1

    params, *trailing = string[pos:].split(':', maxsplit=1)
    params = [*params.split(), *trailing]

    return IRCMessage(tags, name, nick, host, command, params)


# Twitch Clients


loop = asyncio.get_event_loop()


class WebSocketError(Exception): pass


class TwitchIRCSocket:
    def __init__(self):
        self._session = None
        self._ws = None
        self.closed = False
        self.messages = {}
    
    async def send(self, s):
        irc_log.debug(f'> {s}')
        await self._ws.send_str(s + '\r\n')

    async def _on_message(self, msg):
        for line in msg.data.split('\r\n'):
            if len(line) == 0: continue
            irc_log.debug(f'< {line}')

            if line == 'PING :tmi.twitch.tv':
                await self.send('PONG :tmi.twitch.tv')
            
            else:
                msg = parse_irc_message(line)
                await self.on_message(msg)

    async def on_message(self, msg):
        pass

    async def on_connect(self):
        pass

    async def ensure_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()

    async def connect(self):
        backoff = ExponentialBackoff()
        
        while not self.closed:
            try:
                await self.ensure_session()
                self._ws = await self._session.ws_connect('wss://irc-ws.chat.twitch.tv:443')

                await self.on_connect()
                
                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._on_message(msg)
                    
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        raise WebSocketError

            except (OSError, aiohttp.ClientError, asyncio.TimeoutError, WebSocketError):
                irc_log.error(exc_info=True)
                
                if self.closed:
                    return

                irc_log.info('Reconnecting to IRC')
                await asyncio.sleep(backoff.delay())
    
    def close(self):
        self.closed = True

        asyncio.create_task(self._ws.close())
        asyncio.create_task(self._session.close())

    async def login(self, name, token):
        await self.send(f'PASS oauth:{token}')
        await self.send(f'NICK {name}')

    async def request_capabilities(self, *caps):
        await self.send(f'CAP REQ :{" ".join(caps)}')

    async def join_channel(self, channel_name):
        await self.send(f'JOIN #{channel_name}')


class TwitchPubSubSocket:
    def __init__(self):
        self._session = None
        self._ws = None
        self.closed = False
        self._last_pong = 0
    
    async def send(self, o):
        pubsub_log.debug(f'> {o}')
        await self._ws.send_json(o)

    async def ping(self):
        while not self.closed:
            ping_sent_time = time.monotonic()
            await self.send({
                'type': 'PING'
            })

            await asyncio.sleep(10)
            if self._last_pong < ping_sent_time:
                # We didn't get a pong while sleeping
                pubsub_log.warning('No pong, resetting')
                await self._ws.close()

            await asyncio.sleep(180)

    async def _on_message(self, msg):
        pubsub_log.debug(f'< {msg}')
        
        if msg.type == 'PONG':
            self._last_pong = time.monotonic()
        
        elif msg.type == 'RECONNECT':
            await self._ws.close()

        elif msg.type == 'MESSAGE':
            await self.on_message(msg.data.topic, json.loads(msg.data.message, object_hook=Obj))

        elif msg.type == 'RESPONSE':
            pubsub_log.debug(msg)

        else:
            pubsub_log.warning(f'Unknown message type {msg}')

    async def on_message(self, topic, message):
        pass

    async def on_connect(self):
        pass

    async def ensure_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()

    async def connect(self):
        backoff = ExponentialBackoff()
        ping_task = None
        
        while not self.closed:
            try:
                await self.ensure_session()
                self._ws = await self._session.ws_connect('wss://pubsub-edge.twitch.tv')

                await self.on_connect()

                ping_task = asyncio.create_task(self.ping())
                
                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data, object_hook=Obj)
                        await self._on_message(data)
                    
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        raise WebSocketError

            except (OSError, aiohttp.ClientError, asyncio.TimeoutError, WebSocketError):
                pubsub_log.error(exc_info=True)
                ping_task.cancel()
                
                if self.closed:
                    return

                pubsub_log.info('Reconnecting to PubSub')
                await asyncio.sleep(backoff.delay())
    
    def close(self):
        self.closed = True

        asyncio.create_task(self._ws.close())
        asyncio.create_task(self._session.close())

    async def listen_to(self, token, *topics):
        await self.send({
            'type': 'LISTEN',
            'data': {
                'topics': topics,
                'auth_token': token
            }
        })
