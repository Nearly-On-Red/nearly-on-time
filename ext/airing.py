import asyncio
import json
import logging
import time
from collections import namedtuple


import discord
from discord.ext import tasks, commands as cmd
import aiohttp

from helper.common import *


log = logging.getLogger('bot')
loop = asyncio.get_event_loop()


query = '''
query ($ids: [Int], $before: Int) {
  Page(perPage: 50) {
    pageInfo {
      total
      currentPage
      lastPage
      hasNextPage
      perPage
    }
    airingSchedules(notYetAired: true, mediaId_in: $ids, airingAt_lesser: $before, sort: TIME) {
      media {
        id
        title {
          english
          romaji
        }
      }
      episode
      airingAt
    }
  }
}
'''

Episode = namedtuple('Episode', 'media_id title number air_time')


class AiringCog(cmd.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watched_anime = [105932, 106893, 107663, 101348]
        self.scheduled_announcements = {}

        self.reload_upcoming.start()
    
    def cog_unload(self):
        self.reload_upcoming.stop()
        for task in self.scheduled_announcements:
            task.cancel()
    
    @tasks.loop(minutes=30)
    async def reload_upcoming(self):
        # Every 30 minutes we reload the upcoming episodes, in case something changes. (Episode cancelled, etc...)
        async with aiohttp.ClientSession() as session:
            async with session.post('https://graphql.anilist.co', json={
                'query': query,
                'variables': {
                    'ids': self.watched_anime,
                    'before': int(time.time() + 604800) # We only query episodes that air in the next week
                }
            }) as response:
                data = json.loads(await response.text(), object_hook=Obj)

        if not 'data' in data:
            log.error('Invalid anilist response')
            log.error(repr(data))

        for episode_data in data.data.Page.airingSchedules:
            ep = Episode(
                media_id=episode_data.media.id,
                title=episode_data.media.title.english or episode_data.media.title.romaji,
                number=episode_data.episode,
                air_time=episode_data.airingAt
            )

            if (ep.media_id, ep.number) in self.scheduled_announcements:
                old_ep, task = self.scheduled_announcements[ep.media_id, ep.number]

                if old_ep.air_time != ep.air_time:
                    # The air time has changed from the previous time we fetched it.
                    # Therefore, the episode was rescheduled.
                    task.cancel()
                    del self.scheduled_announcements[ep.media_id, ep.number]
                    announce_rescheduling(old_episode, new_episode)

                else:
                    # Otherwise, nothing has changed and we can just continue with the next episode.
                    continue

            task = asyncio.create_task(self.announce_episode(ep))

            self.scheduled_announcements[ep.media_id, ep.number] = ep, task

    async def announce_episode(self, episode):
        await asyncio.sleep(episode.air_time - time.time())
        print(episode)  # TODO send message
        del self.scheduled_announcements[episode.media_id, episode.number]

    async def announce_rescheduling(self, old_episode, new_episode):
        await asyncio.sleep(episode.airingAt - time.time())
        print(episode, 'was rescheduled')  # TODO send message
        del self.scheduled_announcements[media, number]


def setup(bot):
    cog = AiringCog(bot)
    bot.add_cog(cog)
