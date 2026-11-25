from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.action_dispatch import ActionDispatcher
from app.services.scan_dispatch import ScanDispatcher
from app.services.sync_dispatch import SyncDispatcher
from app.temporal.action_dispatcher import get_action_dispatcher
from app.temporal.dispatcher import get_sync_dispatcher
from app.temporal.scan_dispatcher import get_scan_dispatcher

SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Starts sync workflows and manages their schedules. Tests override get_sync_dispatcher.
DispatcherDep = Annotated[SyncDispatcher, Depends(get_sync_dispatcher)]
# Starts ExecuteActionWorkflow on approval. Tests override get_action_dispatcher.
ActionDispatcherDep = Annotated[ActionDispatcher, Depends(get_action_dispatcher)]
# Starts ScanConnectionWorkflow and its schedule. Tests override get_scan_dispatcher.
ScanDispatcherDep = Annotated[ScanDispatcher, Depends(get_scan_dispatcher)]
