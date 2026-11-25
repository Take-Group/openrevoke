"""Activities of ``ScanConnectionWorkflow``. They only call ``app.services.discovery_scan``."""

import uuid

from temporalio import activity

from app.services import discovery_scan
from app.services.discovery_scan import ScanOutcome
from app.temporal.scan_types import FailScanInput, RunScanInput, ScanParams


@activity.defn
async def start_scan_run(params: ScanParams) -> str | None:
    run_id = await discovery_scan.start_run(
        uuid.UUID(params.connection_id), uuid.UUID(params.scan_run_id) if params.scan_run_id else None
    )
    return str(run_id) if run_id else None


@activity.defn
async def run_scan(data: RunScanInput) -> ScanOutcome:
    return await discovery_scan.run(uuid.UUID(data.scan_run_id))


@activity.defn
async def fail_scan_run(data: FailScanInput) -> ScanOutcome:
    return await discovery_scan.fail_run(uuid.UUID(data.scan_run_id), data.error)


SCAN_ACTIVITIES = [start_scan_run, run_scan, fail_scan_run]
