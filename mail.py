import asyncio

import discord

from ...common import *
from ... import module as mod


log = mod.get_logger()


class MailModule(mod.Module):
    def on_load(self):
        self.conf.setdefault('category_id', 0)
        self.conf.setdefault('allowed_role_ids', [])
        self.conf.setdefault('allowed_user_ids', [])
        self.conf.sync()

    @mod.group(name='mail', usage='mail', description='Creates a modmail channel for you, or links you to an existing one')
    async def mail_cmd(self, ctx):
        try:
            requesting_user = ctx.author

            if channel := await self.get_existing_channel(ctx, requesting_user):
                await ctx.send(embed=discord.Embed(
                    description=f'Your channel is {channel.mention}'
                ))

            elif channel := await self.create_modmail_channel(ctx, requesting_user):  
                await ctx.send(embed=discord.Embed(
                    description=f'Your channel is {channel.mention}'
                ))

            else:
                raise RuntimeError("Couldn't create or get channel.")

        except:
            await ctx.send(embed=discord.Embed(
                description=f'Sorry, an error has occured. Please notify hmry in DMs.'
            ))
            raise
    
    async def get_existing_channel(self, ctx, user):
        category = self.bot.get_channel(self.conf['category_id'])
        
        if category is None:
            log.error('Could not search for channels because category is not valid.')
            return None

        channel_name = f'{user.name}-{user.discriminator}'
        return next((channel for channel in category.text_channels if channel.name == channel_name), None)


    async def create_modmail_channel(self, ctx, user):
        category = self.bot.get_channel(self.conf['category_id'])
        
        if category is None:
            log.error('Could not create channel because category is not valid.')
            return None

        guild = category.guild

        channel_name = f'{user.name}-{user.discriminator}'
        return await category.create_text_channel(
            channel_name,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                **{
                    guild.get_member(id): discord.PermissionOverwrite(read_messages=True)
                    for id in (user.id, *self.conf['allowed_user_ids'])
                },
                **{
                    guild.get_role(id): discord.PermissionOverwrite(read_messages=True)
                    for id in self.conf['allowed_role_ids']
                },
            })
