import re
from jinja2 import pass_eval_context
import markupsafe

re_paragraph = re.compile(r'(?:\r\n|\r(?!\n)|\n){2,}')

@pass_eval_context
def nl2br(eval_ctx, value):
    normalized_value = re.sub(r'\r\n|\r|\n', '\n', markupsafe.escape(value))
    html_value = normalized_value.replace('\n', '\n<br />\n')
    if eval_ctx.autoescape:
        return markupsafe.Markup(html_value)
    return html_value