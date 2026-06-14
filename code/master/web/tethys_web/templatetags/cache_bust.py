# =============================================================================
# Cache-busting static tag.
#
# Browsers aggressively cache static assets. Because this project deploys the
# frontend with a plain file copy (not `collectstatic` with a hashing storage),
# a redeployed `common.js`/`main.css` keeps the same URL, so browsers happily
# serve the stale copy until a manual hard-refresh. That bit us once already.
#
# `static_v` behaves like `{% static %}` but appends the source file's
# modification time as a `?v=<mtime>` query string. The URL changes whenever the
# file content does, so the browser fetches the new asset automatically and uses
# its cache the rest of the time. No manual version bumping required.
# =============================================================================

import os

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    '''Like {% static path %} but with a ?v=<mtime> cache-busting suffix.'''
    url = static(path)

    # Source assets live under BASE_DIR/static (the same files the deploy copies
    # into the nginx-served directory), so their mtime tracks each rebuild.
    full_path = os.path.join(settings.BASE_DIR, "static", path)
    try:
        version = int(os.path.getmtime(full_path))
    except OSError:
        # File not found / unreadable: fall back to the plain URL rather than
        # breaking the page.
        return url

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"
