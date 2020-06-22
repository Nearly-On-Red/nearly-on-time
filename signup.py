import discord

from ...common import *
from ... import module as mod


class SignupModule(mod.Module):
    def on_load(self):
        self.conf.setdefault('posts', {})
        self.conf.sync()

    @mod.Module.listener()
    async def on_raw_reaction_add(self, event):
        if (event.channel_id, event.message_id) in self.conf['posts'] and event.user_id != self.bot.user.id:
            channel = self.bot.get_channel(event.channel_id)
            role = channel.guild.get_role(self.conf['posts'][event.channel_id, event.message_id])
            member = channel.guild.get_member(event.user_id)

            await member.add_roles(role, reason='Requested through bot')

    @mod.Module.listener()
    async def on_raw_reaction_remove(self, event):
        if (event.channel_id, event.message_id) in self.conf['posts'] and event.user_id != self.bot.user.id:
            channel = self.bot.get_channel(event.channel_id)
            role = channel.guild.get_role(self.conf['posts'][event.channel_id, event.message_id])
            member = channel.guild.get_member(event.user_id)

            await member.remove_roles(role, reason='Requested through bot')

    @mod.Module.listener()
    async def on_raw_message_delete(self, event):
        if (event.channel_id, event.message_id) in self.conf['posts']:
            del self.conf['posts'][event.channel_id, event.message_id]
            self.conf.sync()

    @mod.group(name='signup')
    async def signup_cmd(self, ctx):
        pass

    @signup_cmd.command(name='create')
    async def create_cmd(self, ctx, role: discord.Role, emoji: str, *, message):
        msg = await ctx.send(embed=discord.Embed(color=getattr(ctx.me, 'color', 0), title=f'{role}', description=f'{message}\n\n*React with {emoji} to receive this role.*'))
        self.conf['posts'][msg.channel.id, msg.id] = role.id
        self.conf.sync()
        await msg.add_reaction(emoji)
