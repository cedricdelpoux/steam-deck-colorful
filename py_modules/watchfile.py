"""Wake up instantly when a file changes, instead of polling its mtime.

No inotify package ships with Decky's bundled Python, but the kernel call
itself needs nothing but ctypes -- so this talks to it directly rather than
adding a dependency for three syscalls.
"""
import asyncio
import ctypes
import os
import struct

try:
    _libc = ctypes.CDLL('libc.so.6', use_errno=True)
except OSError:
    _libc = None   # not Linux (or no glibc) -- watch() below just no-ops

IN_CLOSE_WRITE = 0x00000008
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
_WATCH_MASK = IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE
_EVENT_FMT = 'iIII'   # struct inotify_event { int wd; uint32 mask, cookie, len; }
_EVENT_SIZE = struct.calcsize(_EVENT_FMT)


async def watch(path, on_change):
    """Call `on_change()` (may be async) each time `path` is (re)written.

    Watches its parent directory rather than the file itself: editors and
    config tools often save by writing a temp file and renaming it over the
    original, which swaps the inode instead of modifying it -- a watch on the
    old inode would then go silent forever.

    Runs until cancelled; on any setup failure it just returns, silently
    giving up the instant notification (the caller's own periodic refresh,
    if it has one, still catches the change eventually).
    """
    if _libc is None:
        return
    directory, name = os.path.split(os.path.abspath(path))
    fd = _libc.inotify_init1(0)
    if fd < 0:
        return
    try:
        wd = _libc.inotify_add_watch(fd, directory.encode(), _WATCH_MASK)
        if wd < 0:
            return
        os.set_blocking(fd, False)
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        loop.add_reader(fd, lambda: queue.put_nowait(None))
        try:
            while True:
                await queue.get()
                if _consume(fd, name):
                    result = on_change()
                    if asyncio.iscoroutine(result):
                        await result
        finally:
            loop.remove_reader(fd)
    finally:
        os.close(fd)


def _consume(fd, name):
    """Drain pending events, True if any of them named our file."""
    hit = False
    try:
        data = os.read(fd, 4096)
    except BlockingIOError:
        return False
    offset = 0
    while offset + _EVENT_SIZE <= len(data):
        _wd, _mask, _cookie, length = struct.unpack_from(_EVENT_FMT, data, offset)
        offset += _EVENT_SIZE
        raw = data[offset:offset + length]
        offset += length
        if raw.rstrip(b'\0').decode(errors='replace') == name:
            hit = True
    return hit
