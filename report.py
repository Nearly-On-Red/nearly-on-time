import asyncio
import json
from collections import deque, namedtuple
from datetime import datetime as dt, timezone as tz

import discord

from ...common import *
from ... import module as mod
from . import twitch


Message = namedtuple('Message', 'id sender content timestamp')
Report = namedtuple('Report', 'message reasons discord_id')


MESSAGE_CACHE_SIZE = 1000

class MessageLogger(twitch.TwitchIRCSocket):
    def __init__(self, module, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mod = module
        self.log = module.log

        self._id_queue = deque(maxlen=MESSAGE_CACHE_SIZE)
        self.messages = {}

    async def on_connect(self):
        await self.login(self.mod.conf['twitch_user_name'], self.mod.conf['twitch_oauth_token'])
        await self.request_capabilities('twitch.tv/tags')
        await self.join_channel(self.mod.conf['twitch_channel_name'])

    async def on_message(self, message):
        if message.command != 'PRIVMSG':
            return

        msg_id = message.tags['id']
        msg = Message(msg_id, message.name, message.params[1], int(message.tags['tmi-sent-ts']))
        
        if len(self._id_queue) == MESSAGE_CACHE_SIZE:
            del self.messages[self._id_queue[0]]
        
        self._id_queue.append(msg_id)
        self.messages[msg_id] = msg

class ReportReciever(twitch.TwitchPubSubSocket):
    def __init__(self, module, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mod = module
        self.log = module.log

        self.report_queue = asyncio.Queue()

    async def on_connect(self):
        await self.listen_to(self.mod.conf['twitch_oauth_token'], f'whispers.{self.mod.conf["twitch_user_id"]}')

    async def on_message(self, topic, message):
        if message.type != 'whisper_received':
            return
        
        data = json.loads(message.data, object_hook=Obj)
        sender = data.tags.login
        body = data.body

        args = body.split()
        if args[0] != 'report' or len(args) != 3:
            self.log.warning(f'Unrecognizable whisper from {sender}: {body}')
            return

        await self.report_queue.put((sender, args[1], args[2]))


class ReportModule(mod.Module):
    def on_load(self):
        self.conf.setdefault('twitch_user_name', '')
        self.conf.setdefault('twitch_user_id', '')
        self.conf.setdefault('twitch_oauth_token', '')
        self.conf.setdefault('twitch_channel_name', '')
        self.conf.setdefault('reports_channel_id', 0)
        self.conf.setdefault('reports', {})
        self.conf.setdefault('reasons', {})
        self.conf.sync()

        if len(self.conf['twitch_oauth_token']) == 0:
            raise ValueError("Can't load reports without twitch login details")

        self.ml = MessageLogger(self)
        self.rr = ReportReciever(self)

        self.ml_task = asyncio.create_task(self.ml.connect())
        self.rr_task = asyncio.create_task(self.rr.connect())

        self.post_task = asyncio.create_task(self.post_reports())

    def on_unload(self):
        self.post_task.cancel()

        self.ml_task.cancel()
        self.rr_task.cancel()
    
        self.ml.close()
        self.rr.close()

    async def post_reports(self):
        while True:
            reporter, message_id, reason = await self.rr.report_queue.get()
            previous_report = self.conf['reports'].get(message_id)
            
            channel = self.bot.get_channel(self.conf['reports_channel_id'])
            
            if previous_report is None:
                if message_id not in self.ml.messages:
                    self.log.warning(f"Report of unknown message {message_id} by {reporter} for {reason}")
                    continue

                message = self.ml.messages[message_id]
                reasons = {reason: [reporter]}

            else:
                message = previous_report.message
                reasons = previous_report.reasons

                if reason in reasons and reporter in reasons[reason]:
                    continue

                reasons.setdefault(reason, []).append(reporter)

                if channel and previous_report.discord_id:
                    try:
                        previous_message = await channel.fetch_message(previous_report.discord_id)
                        await previous_message.delete()
                    
                    except discord.NotFound:
                        pass

            
            discord_id = None
            
            if channel:
                report_list = '\n'.join(f' - **{self.conf["reasons"].get(reason) or f"[{reason}]"}** - {", ".join(reporters)}' for reason, reporters in reasons.items())

                embed = discord.Embed(
                    description=f'**{message.sender}**: {message.content}\n\nReported for:\n' + report_list,
                    timestamp=dt.fromtimestamp(message.timestamp/1000, tz=tz.utc))

                discord_id = (await channel.send(embed=embed)).id


            self.conf['reports'][message_id] = Report(message, reasons, discord_id)
            self.conf.sync()
