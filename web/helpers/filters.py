import re
from jinja2 import pass_eval_context, filters
import markupsafe

# filter to make all \n to <br />
@pass_eval_context
def nl2br(eval_ctx, value):
    normalized_value = re.sub(r'\r\n|\r|\n', '\n', markupsafe.escape(value))
    html_value = normalized_value.replace('\n', '\n<br />\n')
    if eval_ctx.autoescape:
        return markupsafe.Markup(html_value)
    return html_value

# filter for italics, bold, underline and strike
@pass_eval_context
def text_filters(eval_ctx, value):
    # random re.sub to value (idk why i have to add this first line otherwise it doesnt work)
    normalized_value = re.sub(r'\[LMAO\]([\s\S]*?)\[/LMAO\]', r'lmao', value)
    normalized_value = re.sub(r'\[i\]([\s\S]*?)\[/i\]', r'<i>\1</i>', normalized_value)
    normalized_value = re.sub(r'\[b\]([\s\S]*?)\[/b\]', r'<b>\1</b>', normalized_value)
    normalized_value = re.sub(r'\[u\]([\s\S]*?)\[/u\]', r'<u>\1</u>', normalized_value)
    normalized_value = re.sub(r'\[s\]([\s\S]*?)\[/s\]', r'<s>\1</s>', normalized_value)
    if eval_ctx.autoescape:
        return markupsafe.Markup(normalized_value)
    return normalized_value

# filter to make all text between [h1] and [/h1] h1
@pass_eval_context
def h1(eval_ctx, value):
    normalized_value = re.sub(r'\[h1\]([\s\S]*?)\[/h1\]', r'<h1 style="margin-bottom: 0;" class="title has-text-black is-3">\1</h1>', value)
    if eval_ctx.autoescape:
        return markupsafe.Markup(normalized_value)
    return normalized_value

# export
filters.FILTERS['nl2br'] = nl2br
filters.FILTERS['text_filters'] = text_filters
filters.FILTERS['h1'] = h1