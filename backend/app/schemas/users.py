"""Panel users and invites, managed by admins."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole
from app.schemas.auth import Email
from app.schemas.common import ApiModel


class InviteCreate(BaseModel):
    email: Email
    role: UserRole = UserRole.USER


class InviteOut(ApiModel):
    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    invite_id: uuid.UUID = Field(validation_alias="id")
    email: str
    role: UserRole
    created_at: datetime
    expires_at: datetime


class InviteCreated(InviteOut):
    link: str = Field(description="Registration link; shown only now. Pass it on yourself, nothing is e-mailed")


class InviteList(BaseModel):
    items: list[InviteOut]


class UserUpdate(BaseModel):
    role: UserRole


class ResetLinkOut(BaseModel):
    link: str = Field(description="One-time /reset-password link; shown only now. Pass it to the person yourself")
    expires_at: datetime
