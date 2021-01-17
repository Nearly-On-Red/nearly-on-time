import discord

# from ...common import *
from ... import module as mod


class SignupModule(mod.Module):
    class Config(mod.Config):
        posts: dict[tuple[int, int], int] = {}

    @mod.Module.listener()
    async def on_raw_reaction_add(self, event):
        if (event.channel_id, event.message_id) in self.conf.posts and event.user_id != self.bot.user.id:
            channel = self.bot.get_channel(event.channel_id)
            role = channel.guild.get_role(self.conf.posts[event.channel_id, event.message_id])

            await event.member.add_roles(role, reason='Requested through bot')

    @mod.Module.listener()
    async def on_raw_reaction_remove(self, event):
        if (event.channel_id, event.message_id) in self.conf.posts and event.user_id != self.bot.user.id:
            channel = self.bot.get_channel(event.channel_id)
            role = channel.guild.get_role(self.conf.posts[event.channel_id, event.message_id])
            member = await channel.guild.fetch_member(event.user_id)

            await member.remove_roles(role, reason='Requested through bot')

    @mod.Module.listener()
    async def on_raw_message_delete(self, event):
        if (event.channel_id, event.message_id) in self.conf.posts:
            del self.conf.posts[event.channel_id, event.message_id]
            await self.conf.commit()

    @mod.group(name='signup', invoke_without_command=True)
    @mod.is_owner()
    async def signup_cmd(self, ctx):
        messages = []
        for (channel_id, message_id), role_id in self.conf.posts.items():
            channel = self.bot.get_channel(channel_id)
            role = channel.guild.get_role(role_id)
            messages.append((role, channel))

        await ctx.send_paginated('Active sign-up posts:\n' + '\n'.join(f' - {role} in #{channel}' for role, channel in messages))

    @signup_cmd.command(name='create')
    @mod.is_superuser()
    async def create_cmd(self, ctx, role: discord.Role, emoji: str, *, message):
        msg = await ctx.send(embed=discord.Embed(color=getattr(ctx.me, 'color', 0), title=f'{role}', description=f'{message}\n\n*React with {emoji} to receive this role.*'))
        self.conf.posts[msg.channel.id, msg.id] = role.id
        await self.conf.commit()
        await msg.add_reaction(emoji)
