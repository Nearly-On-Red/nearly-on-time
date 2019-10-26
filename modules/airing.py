import asyncio
import json
import traceback
from datetime import datetime as dt, timedelta as td

import aiohttp
from discord import Embed

from ..common import *
from .. import module as mod


get_airing_query = '''
query ($show_ids: [Int], $after: Int, $before: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo {
      hasNextPage
    }
    airingSchedules(mediaId_in: $show_ids, airingAt_greater: $after, airingAt_lesser: $before, sort: TIME) {
      media {
        id
        title {
          english
          romaji
        }
        siteUrl
        externalLinks {
          site
          url
        }
        coverImage {
          medium
          color
        }
      }
      episode
      airingAt
    }
  }
}
'''


class AiringModule(mod.Module):
    def on_load(self):
        self.conf.setdefault('channel_id', 0)
        self.conf.setdefault('blacklisted_sites', {'Official Site', 'Twitter'})
        self.conf.setdefault('shows', set())
        self.conf.setdefault('refresh_interval_mins', 5)
        self.conf.sync()

        self.next_check = dt.utcnow()
        self.session = None
        self.fetching_task = mod.loop.create_task(self.fetch_continuously())
        self.pending_announcements = {}

        self.channel = self.bot.get_channel(self.conf['channel_id'])

    def on_unload(self):
        self.fetching_task.cancel()
        
        if self.session:
            self.log.info('Closing session...')
            mod.loop.create_task(self.session.close())
        
        for ann in self.pending_announcements.values():
            ann.cancel()

    async def make_airing_query_request(self, after, before, page):
        self.log.info(f'Fetching episodes from {after} to {before}...')
        async with self.session.post('https://graphql.anilist.co', json={
            'query': get_airing_query,
            'variables': {
              'show_ids': list(self.conf['shows']),
              'after': int(dt.timestamp(after)),
              'before': int(dt.timestamp(before)) - 1,
              'page': page
            }
        }, timeout=aiohttp.ClientTimeout(total=10)) as response:
            resp = json.loads(await response.text(), object_hook=Obj)
            # TODO: Handle http errors here? ~hmry (2019-10-21, 16:05)

            if (
                'data' not in resp or resp.data is None
                or 'errors' in resp and resp.errors not in (None, [])
            ):
                self.log.error(f'Failed to reload episodes! {resp}')
                # TODO: Try exponential backoff here? ~hmry (2019-10-18, 21:24)

            return resp.data.Page

    async def fetch_upcoming_episodes(self):
        from_t = self.next_check
        to_t = dt.utcnow() + td(minutes=self.conf['refresh_interval_mins'])

        self.next_check = to_t

        
        # We can only open sessions in a coroutine, so we do it here instead of on_load
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.log.info('Session opened')

        page_number = 0
        while True:
            data = await self.make_airing_query_request(after=from_t, before=to_t, page=page_number)
            self.log.info(data)

            for ep in data.airingSchedules:
                airing_in_seconds = (dt.utcfromtimestamp(ep.airingAt) - dt.utcnow()).total_seconds()

                handle = mod.loop.call_later(airing_in_seconds, self.announce_episode(ep))
                self.pending_announcements[id(ep)] = handle

            if not data.pageInfo.hasNextPage:
                break
            
            page_number += 1

    async def fetch_continuously(self):
        while True:
            try:
                await self.fetch_upcoming_episodes()
            
            except Exception:
                traceback.print_exc()
    
            sleep_duration = (self.next_check - dt.utcnow()).total_seconds()
            self.log.info(f'Sleeping for {sleep_duration} seconds')
            await asyncio.sleep(sleep_duration)

    async def announce_episode(self, ep):
        del self.pending_announcements[id(ep)]
        channel = self.bot.get_channel(self.conf['channel_id'])
        
        if not channel:
            self.log.warning(f'Announcement for {title} # {number} dropped, invalid channel {self.conf["channel_id"]}')

        anime = ep.media
        title = anime.title.english or anime.title.romaji
        number = ep.episode

        link_list = [f'[[{link.site}]]({link.url})' for link in anime.externalLinks if link.site not in self.conf['blacklisted_sites']]

        embed = Embed(
            title=f'New {title} Episode',
            colour=channel.guild.me.color,
            url=anime.siteUrl,
            description=f'**{title}** Episode **{number}** just aired!\n\n' + ' '.join(link_list),
            timestamp=dt.utcfromtimestamp(ep.airingAt))

        embed.set_thumbnail(url=anime.coverImage.medium)

        await channel.send(embed=embed)
