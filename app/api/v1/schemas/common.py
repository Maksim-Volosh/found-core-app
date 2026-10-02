from typing import Annotated

from pydantic import Field

from app.domain.constants import MAX_INT64

Int64Id = Annotated[int, Field(ge=1, le=MAX_INT64)]
