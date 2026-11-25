"""Query parameters shared by list endpoints."""

from typing import Annotated

from fastapi import Query

SearchQuery = Annotated[str | None, Query(max_length=200, description="Case-insensitive text search")]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]
DEFAULT_LIMIT = 100
