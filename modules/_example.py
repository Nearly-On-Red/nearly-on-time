from ..common import *
from .. import module as mod


class TestModule(mod.Module):
    class Config:
        int_field: int
        str_field: str

    @mod.command(name='test')
    async def test_cmd(self, ctx):
        await ctx.send('Test!')
