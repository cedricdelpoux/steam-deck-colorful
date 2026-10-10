"""Make the plugin's assets reachable from the library UI.

The injected CSS runs inside Steam's own page, which is served from
steamloopback.host -- a virtual host mapped onto Steam's `steamui` folder. So
anything symlinked in there can be referenced by a plain root-relative URL, and
that is how CSS Loader gets theme images on screen too.

The alternative is inlining every render as a data: URI, which works everywhere
but costs about 350 KB of stylesheet per visible tab.
"""
import os

STEAMUI = os.path.expanduser('~/.local/share/Steam/steamui')
LINK_NAME = 'console_panel'


def publish(assets_dir):
    """Expose `assets_dir` under steamloopback.host, returning its URL prefix.

    None when the link can't be made -- the caller then falls back to data URIs.
    """
    if not os.path.isdir(STEAMUI):
        return None
    link = os.path.join(STEAMUI, LINK_NAME)

    try:
        if os.path.islink(link):
            if os.path.realpath(link) == os.path.realpath(assets_dir):
                return '/' + LINK_NAME
            os.unlink(link)
        elif os.path.exists(link):
            return None          # something real is in the way; don't touch it
        os.symlink(assets_dir, link)
    except OSError:
        return None
    return '/' + LINK_NAME


def unpublish():
    """Remove the link again, on uninstall."""
    link = os.path.join(STEAMUI, LINK_NAME)
    try:
        if os.path.islink(link):
            os.unlink(link)
    except OSError:
        pass
