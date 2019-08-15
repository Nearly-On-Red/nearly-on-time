import re
import datetime
import inspect
import logging

import discord
import discord.ext.commands as cmd
from discord.ext.commands.view import StringView

from .common import *
from .module import get_module_class

log = logging.getLogger('bot')

# While this is the actual bot class, most of the functionality is implemented in the various extensions/cogs
# Here we only implement the eval, exec and uptime commands, as well as the mention matching.
# TODO: It might be nice to move these to a "core" cog that can be reloaded. ~hmry (2019-08-14, 02:20)

class NearlyOnTime(cmd.Bot):
    def __init__(self, conf):
        super().__init__(command_prefix='', description='', pm_help=False, help_attrs={})

        super().remove_command('help')

        self.conf = conf
        self.first_ready = None
        self.last_ready = None
        self.last_resume = None

        self.command_regex = None
        self.command_dms_regex = None

        self.modules = {}

        # Utility functions for eval/exec
        # TODO: This is pretty ugly, we should probably move these outside of __init__ ~hmry (2019-08-14, 02:28)

        def clean_code(content):
            content = content.strip()

            if content.startswith('```py'):
                content = content[5:]

            if content.startswith('```'):
                content = content[3:]

            if content.endswith('```'):
                content = content[:-3]

            return content.strip('`').strip()

        def create_env(ctx):
            env = {
                'bot': self,
                'ctx': ctx
            }
            env.update(globals())
            return env

        # Registering built-in commands

        @self.command(name='eval', hidden=True, usage='eval <code>', description='Evaluate a piece of python code')
        @is_superuser()
        async def cmd_eval(ctx, *, code: str):
            code = clean_code(code)

            result = eval(code, create_env(ctx))
            if inspect.isawaitable(result):
                result = await result

            await ctx.send_paginated(result)

        @cmd_eval.error
        async def err_eval(ctx, error):
            if isinstance(error, cmd.CheckFailure):
                pass
            else:
                await ctx.send_paginated(error)

        @self.command(name='exec', hidden=True, usage='exec <code>', description='Execute a piece of python code')
        @is_superuser()
        async def cmd_exec(ctx, *, code: str):
            code = clean_code(code)

            env = create_env(ctx)
            code = f'import asyncio\nasync def _func():\n{textwrap.indent(code, "    ")}'

            exec(code, env)

            result = await env['_func']()

            if result is not None:
                await ctx.send_paginated(result)

        @cmd_exec.error
        async def err_exec(ctx, error):
            if isinstance(error, cmd.CheckFailure):
                pass
            else:
                await ctx.send(error)

        @self.command(name='times', hidden=True, usage='times', description='Show uptime stats')
        async def cmd_times(ctx):
            await ctx.send(f'```prolog\nFirst Ready: {self.first_ready}\nLast Ready:  {self.last_ready}\nLast Resume: {self.last_resume}\nUptime:      {datetime.datetime.utcnow() - self.first_ready}```')

        # Loading initial modules

        for mod in conf.initial_modules:
            try:
                self.load_module(mod)

            except:
                log.exception(f'Failed to load module {mod!r} on startup')
                raise

            else:
                log.info(f'Loaded module {mod!r} on startup')

    def load_module(self, name):
        C = get_module_class(name)

        if name in self.modules:
            self.remove_cog(name)

        self.modules[name] = C
        self.add_cog(C(self))

    def unload_module(self, name):
        self.remove_cog(name)
        if name in self.modules:
            del self.modules[name]

    async def on_ready(self):
        log.info(f'Ready with Username {self.user.name!r}, ID {self.user.id!r}')

        now = datetime.datetime.utcnow()
        if self.first_ready is None:
            self.first_ready = now

        self.last_ready = now

        self.command_regex = re.compile(fr'(?s)^<@!?{self.user.id}>(.*)$')
        self.command_dms_regex = re.compile(fr'(?s)^(?:<@!?{self.user.id}>)?(.*)$')

    async def on_resumed(self):
        log.warning(f'Resumed')
        self.last_resume = datetime.datetime.utcnow()

    async def get_context(self, message, *, cls=cmd.Context):
        # This function is called internally by discord.py.
        # We have to fiddle with it because we are using a dynamic prefix (our mention string)
        # as well as no prefix inside of DMs.
        # The included prefix matching functions could not deal with this case.
        # If it ever becomes possible, we should probably switch to that.

        # Frankly, I don't really remember what I did here, but it might be good
        # to periodically check the get_context method on the base class
        # and port over any changes that happened there. ~hmry (2019-08-14, 02:25)

        if self.command_regex is None:
            return cls(prefix=None, view=None, bot=self, message=message)

        cmd_regex = self.command_dms_regex if message.guild is None else self.command_regex
        match = cmd_regex.match(message.content)

        if not match:
            return cls(prefix=None, view=None, bot=self, message=message)

        view = StringView(match.group(1).strip())
        ctx = cls(prefix=None, view=view, bot=self, message=message)

        if self._skip_check(message.author.id, self.user.id):
            return ctx

        invoker = view.get_word()
        ctx.invoked_with = invoker
        ctx.command = self.all_commands.get(invoker)
        return ctx
