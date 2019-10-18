import discord.ext.commands as cmd
import textwrap


# You can't use escape sequences in f-strings. This makes me sad.
NEW_LINE = '\n'


# TODO: I don't know if this is even used anymore... Remove? ~hmry (2019-08-14, 02:33)
def reverse_dict(d):
    values = {}
    for key, value in d.items():
        if value in values:
            values[value].append(key)
        else:
            values[value] = [key]

    return values

class Obj(dict):
    # This is a dictionary which you can access using . instead of [].
    # Nice for JSON data.
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def is_superuser():
    async def pred(ctx):
        return await ctx.bot.is_owner(ctx.author) or ctx.message.author.id in ctx.bot.conf['superusers']

    return cmd.check(pred)


# I know there is a pagination function included in Discord, but that had some bugs and
# strange design choices, so I wrote my own.
# If all of those are fixed, we should probably use theirs instead.
def paginate(content, prefix='```py\n', suffix='```', *, max_size=2000, line_length=None):
    content = str(content)
    if line_length is None:
        line_length = max_size - len(prefix) - len(suffix) - 2

    if len(content) + len(prefix) + len(suffix) > max_size:
        paginator = cmd.Paginator(prefix=prefix, suffix=suffix, max_size=max_size)
        for line in textwrap.wrap(content, line_length):
            paginator.add_line(line)
        return paginator.pages
    else:
        return [prefix + content + suffix]
