"""Tests for the serializers module."""

import json

import pytest
from pydantic import BaseModel

from travessera.exceptions import RequestValidationError, ResponseValidationError
from travessera.serializers import JSONSerializer, get_serializer


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    id: int
    name: str
    active: bool = True


def test_json_serializer_content_type():
    """Test JSONSerializer content type."""
    serializer = JSONSerializer()
    assert serializer.content_type == "application/json"


def test_json_serializer_basic_types():
    """Test JSONSerializer with basic Python types."""
    serializer = JSONSerializer()

    # Test dict
    data = {"key": "value", "number": 42}
    serialized = serializer.serialize(data)
    assert json.loads(serialized) == data

    # Test list
    data = [1, 2, 3, "four"]
    serialized = serializer.serialize(data)
    assert json.loads(serialized) == data

    # Test string
    data = "hello world"
    serialized = serializer.serialize(data)
    assert json.loads(serialized) == data


def test_json_serializer_pydantic_model():
    """Test JSONSerializer with Pydantic models."""
    serializer = JSONSerializer()

    # Single model
    model = SampleModel(id=1, name="Test")
    serialized = serializer.serialize(model)
    assert json.loads(serialized) == {"id": 1, "name": "Test", "active": True}

    # List of models
    models = [
        SampleModel(id=1, name="One"),
        SampleModel(id=2, name="Two", active=False),
    ]
    serialized = serializer.serialize(models)
    assert json.loads(serialized) == [
        {"id": 1, "name": "One", "active": True},
        {"id": 2, "name": "Two", "active": False},
    ]


def test_json_serializer_error():
    """Test JSONSerializer with non-serializable data."""
    serializer = JSONSerializer()

    # Create a non-serializable object
    class NonSerializable:
        pass

    with pytest.raises(RequestValidationError) as exc_info:
        serializer.serialize(NonSerializable())

    assert "Failed to serialize data to JSON" in str(exc_info.value)


def test_json_deserializer_basic_types():
    """Test JSONSerializer deserialization with basic types."""
    serializer = JSONSerializer()

    # Test dict
    data = b'{"key": "value", "number": 42}'
    result = serializer.deserialize(data, dict)
    assert result == {"key": "value", "number": 42}

    # Test list
    data = b'[1, 2, 3, "four"]'
    result = serializer.deserialize(data, list)
    assert result == [1, 2, 3, "four"]

    # Test string
    data = b'"hello world"'
    result = serializer.deserialize(data, str)
    assert result == "hello world"


def test_json_deserializer_pydantic_model():
    """Test JSONSerializer deserialization to Pydantic models."""
    serializer = JSONSerializer()

    # Single model
    data = b'{"id": 1, "name": "Test"}'
    result = serializer.deserialize(data, SampleModel)
    assert isinstance(result, SampleModel)
    assert result.id == 1
    assert result.name == "Test"
    assert result.active is True

    # List of models
    data = b'[{"id": 1, "name": "One"}, {"id": 2, "name": "Two", "active": false}]'
    result = serializer.deserialize(data, list[SampleModel])
    assert len(result) == 2
    assert all(isinstance(item, SampleModel) for item in result)
    assert result[0].id == 1
    assert result[1].active is False


def test_json_deserializer_invalid_json():
    """Test JSONSerializer with invalid JSON."""
    serializer = JSONSerializer()

    with pytest.raises(ResponseValidationError) as exc_info:
        serializer.deserialize(b'{"invalid": json}', dict)

    assert "Failed to parse JSON" in str(exc_info.value)


def test_json_deserializer_validation_error():
    """Test JSONSerializer with Pydantic validation error."""
    serializer = JSONSerializer()

    # Missing required field
    with pytest.raises(ResponseValidationError) as exc_info:
        serializer.deserialize(b'{"id": 1}', SampleModel)

    assert "Failed to validate response data" in str(exc_info.value)
    assert "errors" in exc_info.value.errors


def test_json_deserializer_type_mismatch():
    """Test JSONSerializer with type mismatch."""
    serializer = JSONSerializer()

    # Expect list, get dict
    with pytest.raises(ResponseValidationError) as exc_info:
        serializer.deserialize(b'{"key": "value"}', list[SampleModel])

    assert "Expected list" in str(exc_info.value)


def test_get_serializer():
    """Test getting serializer from registry."""
    serializer = get_serializer("json")
    assert isinstance(serializer, JSONSerializer)
