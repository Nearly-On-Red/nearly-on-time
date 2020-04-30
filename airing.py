import asyncio
import json
from datetime import datetime as dt, timedelta as td, timezone as tz
from collections import namedtuple

import aiohttp
from discord import Embed

from ...common import *
from ... import module as mod


log = mod.get_logger()


get_airing_query = '''
query ($show_ids: [Int], $from_t: Int, $to_t: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo {
      hasNextPage
    }
    airingSchedules(mediaId_in: $show_ids, airingAt_greater: $from_t, airingAt_lesser: $to_t, sort: TIME) {
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


Episode = namedtuple('Episode', 'title info_url image links number time')


class AiringModule(mod.Module):
    def on_load(self):
        self.conf.setdefault('channel_id', 0)
        self.conf.setdefault('blacklisted_sites', {'Official Site', 'Twitter'})
        self.conf.setdefault('shows', set())
        self.conf.setdefault('refresh_interval_mins', 5)
        self.conf.setdefault('last_check', dt.now(tz.utc))
        self.conf.sync()

        self.session = None
        self.schedule_repeated(self.schedule_episode_announcements, every_delta=td(minutes=self.conf['refresh_interval_mins']))

    def on_unload(self):
        if self.session:
            log.info('Closing session...')
            asyncio.create_task(self.session.close())

    async def schedule_episode_announcements(self):
        # We can only open sessions in a coroutine, so we do it here instead of on_load
        if not self.session:
            self.session = aiohttp.ClientSession()
            log.info('Session opened')

        backoff = mod.ExponentialBackoff()

        from_t = self.conf['last_check']

        while True:
            try:
                to_t = dt.now(tz.utc) + td(minutes=self.conf['refresh_interval_mins'])
                episodes = await self.fetch_upcoming_episodes(from_t, to_t)
                break

            except (OSError, aiohttp.ClientError, asyncio.TimeoutError):
                log.info('Episode request failed, retrying...', exc_info=True)
                await asyncio.sleep(backoff.delay())

        for ep in episodes:
            self.schedule_task(self.announce_episode(ep), at_datetime=ep.time)
        
        self.conf['last_check'] = to_t

    async def fetch_upcoming_episodes(self, from_t, to_t):
        if len(self.conf['shows']) == 0:
            return []

        episodes = []
        page_number = 0

        while True:
            log.debug(f'Fetching episodes from {from_t} to {to_t}...')

            async with self.session.post('https://graphql.anilist.co', json={
                'query': get_airing_query,
                'variables': {
                  'show_ids': list(self.conf['shows']),
                  'from_t': int(dt.timestamp(from_t)),
                  'to_t': int(dt.timestamp(to_t)) + 1,
                  'page': page_number
                }
            }, timeout=aiohttp.ClientTimeout(total=10)) as response:
                resp = json.loads(await response.text(), object_hook=Obj)

                if (
                    'data' not in resp or resp.data is None
                    or 'errors' in resp and resp.errors not in (None, [])
                ):
                    log.error(f'Failed to reload episodes! {resp}')

                data = resp.data.Page
            
            log.debug(data)

            for episode_data in data.airingSchedules:
                media = episode_data.media
                ep = Episode(
                    title=media.title.english or media.title.romaji,
                    info_url=media.siteUrl,
                    image=media.coverImage.medium,
                    links=[(link.site, link.url) for link in media.externalLinks if link.site not in self.conf['blacklisted_sites']],
                    number=episode_data.episode,
                    time=dt.fromtimestamp(episode_data.airingAt, tz.utc),
                )

                episodes.append(ep)

            if not data.pageInfo.hasNextPage:
                break
            
            page_number += 1

        return episodes

    async def announce_episode(self, ep):
        channel = self.bot.get_channel(self.conf['channel_id'])

        if channel:
            log.info(f'Announcing {ep.title}#{ep.number}...')
        
            links = ' '.join(f'[[{name}]]({url})' for name, url in ep.links)

            embed = Embed(
                title=f'New {ep.title} Episode',
                colour=channel.guild.me.color,
                url=ep.info_url,
                description=f'**{ep.title}** Episode **{ep.number}** just aired!\n\n{links}',
                timestamp=ep.time,
            )

            embed.set_thumbnail(url=ep.image)

            await channel.send(embed=embed)

        else:
            log.error(f'Announcement for {ep.title}#{ep.number} dropped, invalid channel {self.conf["channel_id"]}')
