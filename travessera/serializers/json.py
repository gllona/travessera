"""
JSON serializer implementation.

This module provides JSON serialization using Pydantic for type safety
and validation.
"""

import json
from typing import Any, TypeVar, get_args, get_origin

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from travessera.exceptions import RequestValidationError, ResponseValidationError
from travessera.serializers.base import Serializer, register_serializer

T = TypeVar("T")


class JSONSerializer(Serializer):
    """
    JSON serializer using Pydantic for validation.

    This serializer handles conversion between Python objects and JSON,
    with automatic Pydantic model validation when applicable.
    """

    @property
    def content_type(self) -> str:
        """Return the content type for JSON."""
        return "application/json"

    def serialize(self, data: Any) -> bytes:
        """
        Serialize Python data to JSON bytes.

        Args:
            data: The data to serialize

        Returns:
            The serialized JSON bytes

        Raises:
            RequestValidationError: If the data cannot be serialized
        """
        try:
            # If it's a Pydantic model, use its json() method
            if isinstance(data, BaseModel):
                return data.model_dump_json().encode("utf-8")

            # Otherwise, use standard json serialization
            return json.dumps(data, default=self._json_default).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise RequestValidationError(
                f"Failed to serialize data to JSON: {e}",
                {"data": str(data), "error": str(e)},
            ) from e

    def deserialize(self, data: bytes, target_type: type[T]) -> T:
        """
        Deserialize JSON bytes to a Python object.

        Args:
            data: The JSON bytes to deserialize
            target_type: The expected type of the result

        Returns:
            The deserialized object

        Raises:
            ResponseValidationError: If the data cannot be deserialized
        """
        try:
            # First, parse the JSON
            parsed = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ResponseValidationError(
                f"Failed to parse JSON: {e}",
                {"data": data[:100].decode("utf-8", errors="replace"), "error": str(e)},
            ) from e

        # Handle different target types
        try:
            # If target_type is a Pydantic model, use it for validation
            if isinstance(target_type, type) and issubclass(target_type, BaseModel):
                return target_type.model_validate(parsed)

            # Handle List[Model] or list[Model]
            origin = get_origin(target_type)
            if origin in (list, list):
                args = get_args(target_type)
                if (
                    args
                    and isinstance(args[0], type)
                    and issubclass(args[0], BaseModel)
                ):
                    # It's List[SomePydanticModel]
                    model_class = args[0]
                    if isinstance(parsed, list):
                        return [model_class.model_validate(item) for item in parsed]
                    else:
                        raise ResponseValidationError(
                            f"Expected list, got {type(parsed).__name__}",
                            {"expected": "list", "actual": type(parsed).__name__},
                        )

            # For other types, return as-is (basic type validation)
            if target_type in (int, float, str, bool, dict, list) and not isinstance(
                parsed, target_type
            ):
                raise ResponseValidationError(
                    f"Expected {target_type.__name__}, got {type(parsed).__name__}",
                    {"expected": target_type.__name__, "actual": type(parsed).__name__},
                )

            return parsed

        except PydanticValidationError as e:
            raise ResponseValidationError(
                f"Failed to validate response data: {e}", {"errors": e.errors()}
            ) from e
        except Exception as e:
            raise ResponseValidationError(
                f"Failed to deserialize response: {e}", {"error": str(e)}
            ) from e

    def _json_default(self, obj: Any) -> Any:
        """
        Default JSON encoder for non-standard types.

        Args:
            obj: The object to encode

        Returns:
            A JSON-serializable representation

        Raises:
            TypeError: If the object cannot be serialized
        """
        # Handle Pydantic models
        if isinstance(obj, BaseModel):
            return obj.model_dump()

        # Handle datetime
        if hasattr(obj, "isoformat"):
            return obj.isoformat()

        # Handle UUID
        if hasattr(obj, "hex"):
            return str(obj)

        # Handle Enum
        if hasattr(obj, "value"):
            return obj.value

        # Let the default encoder handle it (will raise TypeError)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Register the JSON serializer
register_serializer("json", JSONSerializer())
