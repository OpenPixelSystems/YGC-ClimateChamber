import asyncio
import time
from typing import Optional, Any


class AsyncRunner:
    def __init__(self, interval: float = 1.0):
        """
        Initialize the AsyncRunner class with a specific interval.

        Args:
            interval: Time in seconds between function executions
        """
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the background task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_forever())

    async def stop(self):
        """Stop the background task."""
        if self._running and self._task:
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_forever(self):
        """Run the task function in an infinite loop."""
        while self._running:
            await self.task()
            await asyncio.sleep(self.interval)

    async def task(self):
        """
        Override this method in subclasses to implement the task.
        """
        print("Default task running at:", time.strftime("%H:%M:%S"))

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()