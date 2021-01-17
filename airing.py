import asyncio
import json
import string
from datetime import datetime, timedelta, timezone
from collections import namedtuple

import aiohttp
from discord import Embed

from ...common import Obj
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


Episode = namedtuple('Episode', 'anilist_id title info_url image links number time')
AnnouncementAction = namedtuple('AnnouncementAction', 'channel_id rename_pattern')


class CustomFormatter(string.Formatter):
    def format_field(self, value, format_spec):
        if format_spec.startswith('offset'):
            if (o := format_spec.find(':')) != -1:
                offset = int(format_spec[6:o])
                return self.format_field(value + offset, format_spec[o+1:])
            
            offset = int(format_spec[6:])
            return format(value + offset)
        
        else:
            return super().format_field(value, format_spec)

fmt = CustomFormatter()


class AiringModule(mod.Module):
    class Config(mod.Config):
        blacklisted_sites: set[str] = {'Official Site', 'Twitter'}
        shows: dict[int, AnnouncementAction] = {}
        refresh_interval: timedelta = timedelta(minutes=5)
        last_check: datetime = datetime.now(timezone.utc)
    
    async def on_load(self):
        self.session = aiohttp.ClientSession()
        log.info('Session opened')

        self.schedule_repeated(self.schedule_episode_announcements, every_delta=self.conf.refresh_interval)

    async def on_unload(self):
        if self.session:
            log.info('Closing session...')
            await self.session.close()

    async def schedule_episode_announcements(self):
        backoff = mod.ExponentialBackoff()
        from_t = self.conf.last_check

        while True:
            try:
                to_t = datetime.now(timezone.utc) + self.conf.refresh_interval
                episodes = await self.fetch_upcoming_episodes(from_t, to_t)
                break

            except (OSError, aiohttp.ClientError, asyncio.TimeoutError):
                log.info('Episode request failed, retrying...', exc_info=True)
                await asyncio.sleep(backoff.delay())

        for ep in episodes:
            self.schedule_task(self.announce_episode(ep), at_datetime=ep.time)
        
        self.conf.last_check = to_t
        await self.conf.commit()

    async def fetch_upcoming_episodes(self, from_t, to_t):
        if len(self.conf.shows) == 0:
            return []

        episodes = []
        page_number = 0

        while True:
            log.debug(f'Fetching episodes from {from_t} to {to_t}...')

            async with self.session.post('https://graphql.anilist.co', json={
                'query': get_airing_query,
                'variables': {
                  'show_ids': list(self.conf.shows),
                  'from_t': int(datetime.timestamp(from_t)),
                  'to_t': int(datetime.timestamp(to_t)) + 1,
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
                    anilist_id=media.id,
                    title=media.title.english or media.title.romaji,
                    info_url=media.siteUrl,
                    image=media.coverImage.medium,
                    links=[(link.site, link.url) for link in media.externalLinks if link.site not in self.conf.blacklisted_sites],
                    number=episode_data.episode,
                    time=datetime.fromtimestamp(episode_data.airingAt, timezone.utc),
                )

                episodes.append(ep)

            if not data.pageInfo.hasNextPage:
                break
            
            page_number += 1

        return episodes

    async def announce_episode(self, ep):
        actions = self.conf.shows.get(ep.anilist_id)

        if isinstance(actions, AnnouncementAction):
            actions = (actions, )

        log.info(f'Announcing {ep.title}#{ep.number}...')

        for action in actions:
            channel = self.bot.get_channel(action.channel_id)
            if channel is None:
                log.error(f'Announcement for {ep.title}#{ep.number} dropped, invalid channel {action.channel_id}')
                return
        
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

            if action.rename_pattern is not None:
                await channel.edit(name=fmt.format(action.rename_pattern, ep=ep))
