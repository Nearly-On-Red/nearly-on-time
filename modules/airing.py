import asyncio
import json
from datetime import datetime as dt, timedelta as td

import aiohttp

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
        self.fetching_task = mod.loop.create_task(self.fetch_upcoming())
        self.pending_announcements = []

        self.channel = self.bot.get_channel(self.conf['channel_id'])

    def on_unload(self):
        self.fetching_task.cancel()
        self.session.close()
        for ann in self.pending_announcements:
            ann.cancel()

    async def fetch_upcoming(self):
        self.log.info('Reloading episodes...')
        t_now = self.next_check
        t_next = t_now + td(minutes=self.conf['refresh_interval_mins'])

        self.next_check = t_next

        # We can only open sessions in a coroutine, so we do it here instead of on_load
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.log.info('Session opened')

        page_number = 0
        while True:
            async with self.session.post('https://graphql.anilist.co', json={
                'query': get_airing_query,
                'variables': {
                  'show_ids': self.conf['shows'],
                  'after': t_now,
                  'before': t_next + 1,
                  'page': page_number
                }
            }) as response:
                resp = json.loads(await response.text(), object_hook=Obj)
                
                if 'data' not in resp:
                    self.log.error('Failed to reload episodes!')
                    break  # TODO: Try exponential backoff here ~hmry (2019-10-18, 21:24)

                data = resp.data

            for ep in data.airingSchedules:
                airing_in_seconds = (
                    dt.utcfromtimestamp(ep.airingAt) - dt.utcnow()
                ).seconds

                mod.loop.call_later(airing_in_seconds, announce_episode(ep))

            if data.hasNextPage:
                page_number += 1
                continue

            break

        await asyncio.sleep((t_next - dt.utcnow()).seconds)

    async def announce_episode(self, ep):
        title = ep.media.title.english
        number = ep.episode
        link_list = [f'[[{link.site}]]({link.url})' for link in ep.externalLinks if link.site not in self.conf.blacklisted_sites]

        embed = Embed(
            title=f'New {title} Episode',
            colour=self.conf['channel'].guild.me.color,
            url=data.data.Media.siteUrl,
            description=f'**{title}** Episode **{number}** just aired!\n\n' + ' '.join(link_list),
            timestamp=datetime.utcfromtimestamp(ep.airingAt))

        embed.set_thumbnail(url=ep.media.coverImage.medium)

        await self.conf['channel'].send(embed=embed)
