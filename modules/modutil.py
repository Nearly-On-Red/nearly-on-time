from ..common import *
from .. import module as mod


nl = '\n'


class ModUtilModule(mod.Module):
    def __init__(self, bot):
        self.bot = bot

    @mod.group(name='modules', hidden=True, invoke_without_command=True)
    @is_superuser()
    async def cmd_modules(self, ctx):
        await ctx.send(f'```Loaded modules:\n{nl.join(self.bot.modules)}```')

    @cmd_modules.command(name='load')
    @is_superuser()
    async def cmd_load(self, ctx, module: str):
        try:
            self.bot.load_module(module)
        
        except Exception:
            await ctx.add_success_reaction(False)
            raise
        
        else:
            await ctx.add_success_reaction(True)

    @cmd_modules.command(name='reload_all')
    @is_superuser()
    async def cmd_reload_all(self, ctx):
        for modules in self.bot.modules[:]:
            try:
                self.bot.load_module(module)
            
            except Exception:
                await ctx.add_success_reaction(False)
                raise

        await ctx.add_success_reaction(True)

    @cmd_modules.command(name='unload')
    @is_superuser()
    async def cmd_unload(self, module: str):
        if module not in self.bot.modules:
            await ctx.add_success_reaction(False)

        self.bot.unload_module(module)
        await ctx.add_success_reaction(True)
