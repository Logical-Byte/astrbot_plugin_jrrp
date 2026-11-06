"""Beijing-time clock with an optional offset taken from bjtime.org.cn."""

from __future__ import annotations

import asyncio
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

BEIJING = timezone(timedelta(hours=8))

#: Endpoint used by the reference plugin to read a server ``Date`` header.
SYNC_URL = "https://www.bjtime.org.cn"

#: User agent the reference plugin sends, kept so the endpoint behaves the same.
SYNC_USER_AGENT = "AmiyaBot-Jrrp/1.0"


class Clock:
    """Provide the current Beijing time, optionally corrected by a server header.

    Attributes:
        logger: Logger used for sync diagnostics.
    """

    def __init__(
        self, logger: logging.Logger | None = None, *, timeout: float = 5.0
    ) -> None:
        """Store the sync policy; no request is made yet.

        Args:
            logger: Logger used for sync diagnostics.
            timeout: Network timeout of the sync request in seconds.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.timeout = timeout
        self._offset = 0.0
        self._synced = False

    @property
    def synced(self) -> bool:
        """Whether the last sync attempt succeeded."""
        return self._synced

    @property
    def offset(self) -> float:
        """Seconds added to the local clock, zero when not synced."""
        return self._offset

    def _fetch(self) -> float | None:
        """Read the ``Date`` header of the sync endpoint.

        Returns:
            The difference between server and local time in seconds, or
            ``None`` when the header is missing.
        """
        request = urllib.request.Request(
            SYNC_URL, headers={"User-Agent": SYNC_USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            header = response.headers.get("Date")
        if not header:
            return None
        server = datetime.strptime(header, "%a, %d %b %Y %H:%M:%S GMT").replace(
            tzinfo=timezone.utc
        )
        return (server.astimezone(BEIJING) - datetime.now(BEIJING)).total_seconds()

    async def sync(self) -> None:
        """Try to align with the time server, silently keeping local time on failure."""
        offset: float | None = None
        last: Exception | None = None
        # The first TLS handshake to this host is sometimes slow, so retry once.
        for _ in range(2):
            try:
                offset = await asyncio.to_thread(self._fetch)
                break
            except Exception as exc:  # noqa: BLE001 - any network failure is non-fatal
                last = exc
        if offset is None and last is not None:
            self.logger.warning(
                "time sync failed (%s: %s), using local clock",
                type(last).__name__,
                last,
            )
            self._synced = False
            return
        if offset is None:
            self.logger.warning("time sync returned no Date header, using local clock")
            self._synced = False
            return
        self._offset = offset
        self._synced = True
        self.logger.info("time sync ok, offset %+.3f s", offset)

    def now(self) -> datetime:
        """Return the current Beijing time.

        Returns:
            The local clock plus the measured offset.
        """
        return datetime.now(BEIJING) + timedelta(
            seconds=self._offset if self._synced else 0.0
        )

    def stamp(self, fmt: str = "%y%m%d") -> str:
        """Format the current Beijing time.

        Args:
            fmt: ``strftime`` pattern.

        Returns:
            The formatted timestamp.
        """
        return self.now().strftime(fmt)
