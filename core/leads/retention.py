"""How long the bot keeps what people wrote: the text, author and links of a lead go after 30 days, counts stay."""
import asyncio
import logging
import time

from core.database.queries import purge_old_leads
from core.text import plural

RETENTION_SECONDS = 30 * 24 * 3600
PURGE_EVERY_SECONDS = 24 * 3600


async def run_purge(now=time.time, sleep=asyncio.sleep):
    """Erases old leads at startup, then once a day. Nobody awaits this task, so errors are logged here."""
    while True:
        try:
            erased = await purge_old_leads(before=int(now()) - RETENTION_SECONDS)
            logging.info(f"Erased the text of {plural(erased, 'old lead')}")
        except Exception:
            logging.exception("Erasing old leads failed")
        await sleep(PURGE_EVERY_SECONDS)
