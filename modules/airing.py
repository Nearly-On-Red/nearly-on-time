import asyncio
import json
import logging
import time
from datetime import datetime

import aiohttp
import feedparser
from discord import Embed

from ..common import *
from .. import module as mod


log = logging.getLogger('bot')
loop = asyncio.get_event_loop()


blacklisted_sites = (
    'Official Site',
    'Twitter'
)


class AiringModule(mod.Module):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.last_episodes = set()

        self.reload_epsiodes.start()

    def on_unload(self):
        self.reload_epsiodes.stop()
    
    @mod.loop(minutes=5)
    async def reload_epsiodes(self):
        log.info('Reloading episodes')
        # We need to open the session in a coroutine, so we do it here instead of __init__
        if self.session is None:
            self.session = aiohttp.ClientSession()
        log.info('Session opened')

        async with self.session.get('https://www.livechart.me/feeds/episodes') as response:
            feed = feedparser.parse(await response.text())

        episodes = set()

        for entry in feed.entries:
            episodes.add(entry.id)

            if entry.id in self.last_episodes:
                continue

            await self.announce_episode(entry)

        self.last_episodes = episodes

    async def announce_episode(self, entry):
        title, number = entry.title.strip().rsplit('#', maxsplit=1)
        title = title.strip()
        number = int(number)

        channel = self.bot.get_channel(self.bot.conf.announcements.airing.channel)

        async with self.session.post('https://graphql.anilist.co', json={
            'query': 'query($name:String){Media(search:$name){siteUrl externalLinks{site url}}}',
            'variables': {
                'name': title
            }
        }) as response:
            data = json.loads(await response.text(), object_hook=Obj)

        link_list = [f'[[{link.site}]]({link.url})' for link in data.data.Media.externalLinks if link.site not in blacklisted_sites]

        description = f'**{title}** Episode **{number}** just aired!\n\n'

        embed = Embed(
            title=f'New {title} Episode',
            colour=channel.guild.me.color,
            url=data.data.Media.siteUrl,
            description=description + ' '.join(link_list),
            timestamp=datetime.fromtimestamp(time.mktime(entry.published_parsed)))

        embed.set_thumbnail(url=entry.media_thumbnail[0]['url'])

        await channel.send(embed=embed)
