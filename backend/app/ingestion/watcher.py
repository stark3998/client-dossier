# backend/app/ingestion/watcher.py
import asyncio
import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.ingestion.parser import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class _IngestionHandler(FileSystemEventHandler):

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop
        self._debounce: dict[str, asyncio.TimerHandle] = {}

    def _schedule(self, path: str):
        if path in self._debounce:
            self._debounce[path].cancel()
        handle = self._loop.call_later(2.0, self._enqueue, path)
        self._debounce[path] = handle

    def _enqueue(self, path: str):
        self._debounce.pop(path, None)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, path)

    def _is_supported(self, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS

    def on_created(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._schedule(event.src_path)


class FileWatcher:

    def __init__(self, watch_path: str):
        self._watch_path = watch_path
        self._queue: asyncio.Queue = asyncio.Queue()
        self._observer: Observer | None = None

    def start(self):
        if not os.path.isdir(self._watch_path):
            logger.warning("Watch path does not exist: %s", self._watch_path)
            return

        loop = asyncio.get_event_loop()
        handler = _IngestionHandler(self._queue, loop)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_path, recursive=True)
        self._observer.start()
        logger.info("File watcher started: %s", self._watch_path)

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("File watcher stopped")

    @property
    def queue(self) -> asyncio.Queue:
        return self._queue
