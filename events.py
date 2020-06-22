# TODO Don't forget to remove this ~hmry (2019-08-16, 01:11)
raise NotImplementedError("The events module isn't functional yet.")

from collections import namedtuple
from datetime import datetime

import discord
from dateutil import tz

from ...common import *
from ... import module as mod


Location = namedtuple('Location', 'url icon_url color')
locations = {
    'Twitch Channel': ('https://i.imgur.com/DKfwzn4.png', 0x6441a4, 'https://www.twitch.tv/nearlyonred')
}


class Event:
    def __init__(self):
        self.title = None
        self.description = None
        self.start_time = None
        self.end_time = None
        self.location = None

    def __repr__(self):
        return f'({self.title} @ {self.location} @ {self.start_time} - {self.end_time})'


class EventsModule(mod.Module):
    def __init__(self, bot):
        self.bot = bot
        self.events = []
        self.reload_events()

    @mod.group(name='events', invoke_without_command=True)
    @mod.is_owner()
    async def events_cmd(self, ctx):
        await ctx.send(content="__***Upcoming Events:***__")

        for event in sorted(self.events, key=lambda x: x.start_time):
            loc_img, loc_color, loc_url = locations.get(event.location)

            embed = discord.Embed(
                title=event.title.strip(),
                colour=discord.Colour(loc_color),
                url=loc_url,
                description=event.description.strip() + f'\n\n*{event.end_time - event.start_time}, starting at:*',
                timestamp=event.start_time)

            embed.set_author(name=event.location, url=loc_url, icon_url=loc_img)
            await ctx.send(embed=embed)
        

    @events_cmd.command(name='reload')
    @mod.is_owner()
    async def reload_cmd(self, ctx):
        self.reload_events()

    def reload_events(self):
        # TODO Get the info from the export plugin ~hmry (2019-08-16, 01:11)
        # ical = www.nearlyonred.com/events/list/?ical=1&tribe_display=custom&start_date=2019&end_date=2100

        ical_elements = [tuple(line.split(':', maxsplit=1)) for line in ical.split('\n')]

        curr_event = None
        for element in ical_elements:
            k, v  = element

            if element == ('BEGIN', 'VEVENT'):
                curr_event = Event()

            elif element == ('END', 'VEVENT'):
                self.events.append(curr_event)

            elif k == 'SUMMARY':
                curr_event.title = v

            elif k == 'DESCRIPTION':
                curr_event.description = v.replace('\\n', '\n')

            elif k.startswith('DTSTART'):
                time_zone = tz.gettz(dict(x.split('=', maxsplit=1) for x in k.split(';', maxsplit=1)[1:])['TZID'])
                time = datetime.strptime(v, '%Y%m%dT%H%M%S').astimezone(time_zone)

                curr_event.start_time = time

            elif k.startswith('DTEND'):
                time_zone = tz.gettz(dict(x.split('=', maxsplit=1) for x in k.split(';', maxsplit=1)[1:])['TZID'])
                time = datetime.strptime(v, '%Y%m%dT%H%M%S').astimezone(time_zone)

                curr_event.end_time = time

            elif k == 'LOCATION':
                curr_event.location = v
