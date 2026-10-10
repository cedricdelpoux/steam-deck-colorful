"""RetroAchievements web API, as used by the panel.

The key is handed in by the caller (plugin settings), never read from a file
in the repo.
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://retroachievements.org/API/%s.php'
USER_AGENT = 'Colorful/0.1'   # Cloudflare rejects urllib's default agent


def _ssl_context():
    """Decky Loader is a frozen Python binary whose bundled OpenSSL doesn't
    reliably find SteamOS's real CA bundle via the usual default lookup (seen
    live as CERTIFICATE_VERIFY_FAILED even though the OS's own store is fine)
    -- point it at the actual system bundle explicitly instead of guessing."""
    for path in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt'):
        if os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


_SSL_CONTEXT = _ssl_context()


class RA:
    def __init__(self, key, user, cache_dir='/tmp/ra-cache'):
        self.key, self.user, self.cache_dir = key, user, cache_dir
        self._indexes = {}

    def call(self, endpoint, **params):
        params.update(y=self.key, z=self.user)
        req = urllib.request.Request(BASE % endpoint + '?' + urllib.parse.urlencode(params),
                                     headers={'User-Agent': USER_AGENT})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60, context=_SSL_CONTEXT) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 3:
                    raise
                time.sleep(int(e.headers.get('Retry-After') or 5 * (attempt + 1)))

    def hash_index(self, console_id, max_age=7 * 86400):
        """md5 -> game, for every hash RA links to a game on this console.

        Games without achievements are kept on purpose: a supported dump whose
        set is unreleased is not the same as an unsupported dump.
        """
        if console_id in self._indexes:
            return self._indexes[console_id]
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, 'console-%d-all.json' % console_id)
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age:
            with open(path) as f:
                games = json.load(f)
        else:
            games = self.call('API_GetGameList', i=console_id, h=1)
            with open(path, 'w') as f:
                json.dump(games, f)
        index = {h.lower(): g for g in games for h in (g.get('Hashes') or [])}
        self._indexes[console_id] = index
        return index

    def verify_profile(self):
        """Validate the key/user pair against API_GetUserProfile.

        Used by the settings sheet's "Connect" button -- not cached, since it
        exists specifically to check credentials the user just typed in.
        """
        try:
            profile = self.call('API_GetUserProfile', u=self.user)
        except urllib.error.HTTPError as e:
            return {'ok': False,
                    'error': 'Invalid API key' if e.code in (401, 403) else 'HTTP %d' % e.code}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        if not profile or not profile.get('User'):
            return {'ok': False, 'error': 'User not found'}
        return {
            'ok': True,
            'user': profile['User'],
            'avatar': 'https://media.retroachievements.org' + (profile.get('UserPic') or ''),
            # API_GetUserProfile splits points into hardcore (TotalPoints) and
            # softcore (TotalSoftcorePoints) -- most emulators here don't
            # enforce hardcore mode, so a hardcore-only user is left showing
            # 0 despite having real points. There's no "Rank" field on this
            # endpoint at all (confirmed against the live API), so it's
            # dropped rather than always showing null.
            'points': (profile.get('TotalPoints') or 0) + (profile.get('TotalSoftcorePoints') or 0),
            'member_since': profile.get('MemberSince'),
        }

    def user_progress(self):
        """GameID -> progress entry, in one paginated call rather than one per game."""
        out, offset = {}, 0
        while True:
            page = self.call('API_GetUserCompletionProgress', u=self.user, c=500, o=offset)
            for g in page.get('Results', []):
                out[g['GameID']] = g
            offset += page.get('Count', 0)
            if not page.get('Count') or offset >= page.get('Total', 0):
                return out
