"""Activity of ``GoogleCloudSetupWorkflow``: the browser run in ``app.services.google_cloud_setup.runner``."""

import asyncio
import contextlib

from temporalio import activity

from app.services.google_cloud_setup import runner
from app.temporal.dispatcher import get_sync_dispatcher
from app.temporal.scan_dispatcher import get_scan_dispatcher

HEARTBEAT_SECONDS = 10


@activity.defn
async def run_google_cloud_setup() -> None:
    async def keep_alive() -> None:
        while True:
            activity.heartbeat()
            await asyncio.sleep(HEARTBEAT_SECONDS)

    beat_task = asyncio.create_task(keep_alive())
    try:
        await runner.run(activity.heartbeat, get_sync_dispatcher(), get_scan_dispatcher())
    finally:
        beat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await beat_task


GOOGLE_SETUP_ACTIVITIES = [run_google_cloud_setup]
