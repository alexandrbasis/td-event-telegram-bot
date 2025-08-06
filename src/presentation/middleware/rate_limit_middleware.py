import asyncio
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes


class RateLimitMiddleware:
    def __init__(self, limit: float = 1.0):
        self.limit = limit
        self._last: dict[int, float] = defaultdict(lambda: 0.0)

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = asyncio.get_event_loop().time()
        if now - self._last[user_id] < self.limit:
            return None
        self._last[user_id] = now
        return update, context
