from ..common import *
from .. import module as mod


class TestModule(mod.Module):
    def on_load():
        self.config.setdefault('used_count', 0)
        self.config.sync()

    @mod.command(name='test')
    async def test_cmd(self, ctx):
        self.used_count += 1
        await ctx.send(f'Test has been used {count} times!')
