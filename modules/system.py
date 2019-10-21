import subprocess as subp
import os
from shlex import quote

from ..common import *
from .. import module as mod


class SystemModule(mod.Module):
    @mod.command(name='update')
    @is_superuser()
    async def update_cmd(self, ctx):
        await ctx.add_success_reaction(not subp.call(['git', 'fetch', '--all']) and not subp.call(['git', 'reset', '--hard', 'origin']))

    @mod.command(name='restart')
    @is_superuser()
    async def restart_cmd(self, ctx):
        # Normally, using os.system is not a good idea.
        # I think it's fine in this case because we don't
        # have any user controlled data and the command shuts down
        # the program anyway.
        # I tried using subprocess here, but it didn't work.
        # ~hmry (2019-10-21, 02:12)
        os.system('systemctl --user restart ' + quote(f'nearlybot@{self.bot.profile}'))
