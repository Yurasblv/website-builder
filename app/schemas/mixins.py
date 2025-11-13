import json
from typing import Any

from pydantic import model_validator


class StrToJSONMixin:
    """Converts a string to a JSON object."""

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value: Any) -> Any:
        return cls(**json.loads(value)) if isinstance(value, str) else value
