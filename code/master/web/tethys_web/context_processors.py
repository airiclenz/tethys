"""Custom template context processors for the Tethys web app.

Registered in ``settings.TEMPLATES[...]['OPTIONS']['context_processors']`` so the
returned keys are available in every template that is rendered through Django.
"""

from globals.config import version


def app_version(request):
    """Expose the release version (single source of truth: ``globals/config.py``)
    to every template as ``tethys_version``.

    ``version`` is a ``packaging.version.Version``; templates need a plain string,
    and it is the same value ``GET /api/version/`` reports. Sourcing the footer and
    the About dialog from here means neither can drift from the released version.
    """
    return {"tethys_version": str(version)}
