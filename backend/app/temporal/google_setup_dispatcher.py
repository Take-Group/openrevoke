"""Starts ``GoogleCloudSetupWorkflow`` (one at a time: fixed workflow ID)."""

from temporalio.common import WorkflowIDReusePolicy

from app.config import settings
from app.temporal.client import get_temporal_client
from app.temporal.google_setup_workflow import GoogleCloudSetupWorkflow

WORKFLOW_ID = "google-cloud-setup"


async def start_google_cloud_setup() -> None:
    client = await get_temporal_client()
    await client.start_workflow(
        GoogleCloudSetupWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=settings.temporal_task_queue,
        id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
    )
