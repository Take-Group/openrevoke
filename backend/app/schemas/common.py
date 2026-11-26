"""Shared schema building blocks: money, references, list envelopes."""

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, WithJsonSchema

from app.models.enums import AccountStatus, PersonStatus

CENT = Decimal("0.01")


def format_money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


# Money in responses: a decimal string with two places, e.g. "123.40".
Money = Annotated[
    Decimal,
    PlainSerializer(format_money, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^-?\d+\.\d{2}$", "examples": ["123.40"]}),
]

# Money in requests: a decimal string (a JSON number is also accepted).
MoneyInput = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2),
    WithJsonSchema({"type": "string", "pattern": r"^\d{1,10}(\.\d{1,2})?$", "examples": ["12.50"]}),
]

Currency = Annotated[
    str,
    Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$", description="ISO 4217 code, e.g. PLN, USD"),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoneyAmount(ApiModel):
    currency: str
    amount: Money


class AppRef(ApiModel):
    app_id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = Field(
        default=None, description="Uploaded logo, else the catalog's; null without one (show initials)"
    )


class PersonRef(ApiModel):
    person_id: uuid.UUID
    first_name: str
    last_name: str
    primary_email: str
    status: PersonStatus


class AccountRef(ApiModel):
    account_id: uuid.UUID
    email: str | None
    username: str | None
    display_name: str | None
    status: AccountStatus


class ErrorResponse(BaseModel):
    detail: str
