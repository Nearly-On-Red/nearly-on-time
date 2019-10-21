from ..common import *
from .. import module as mod


class ModUtilModule(mod.Module):
    @mod.group(name='modules', hidden=True, invoke_without_command=True)
    @is_superuser()
    async def modules_cmd(self, ctx):
        await ctx.send(f'```Loaded modules:\n{NEW_LINE.join(self.bot.modules)}```')

    @modules_cmd.command(name='load')
    @is_superuser()
    async def load_cmd(self, ctx, module: str):
        try:
            self.bot.load_module(module)
        
        except Exception:
            await ctx.add_success_reaction(False)
            raise
        
        else:
            await ctx.add_success_reaction(True)

    @modules_cmd.command(name='reload_all')
    @is_superuser()
    async def reload_all_cmd(self, ctx):
        for modules in self.bot.modules[:]:
            try:
                self.bot.load_module(module)
            
            except Exception:
                await ctx.add_success_reaction(False)
                raise

        await ctx.add_success_reaction(True)

    @modules_cmd.command(name='unload')
    @is_superuser()
    async def unload_cmd(self, ctx, module: str):
        if module not in self.bot.modules:
            await ctx.add_success_reaction(False)
            return

        self.bot.unload_module(module)
        await ctx.add_success_reaction(True)
