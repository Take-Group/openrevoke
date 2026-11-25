"""Activity of ``CheckForUpdateWorkflow``. It only calls ``app.services.update_check``."""

from temporalio import activity

from app.services import update_check


@activity.defn
async def check_for_update() -> str:
    return await update_check.check()


UPDATE_CHECK_ACTIVITIES = [check_for_update]
