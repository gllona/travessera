"""
Base serializer protocol and utilities.

This module defines the protocol that all serializers must implement
to work with Travessera.
"""

from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

T = TypeVar("T")


class Serializer(ABC):
    """
    Abstract base class for serializers.

    All serializers must implement this interface to be used with Travessera.
    """

    @property
    @abstractmethod
    def content_type(self) -> str:
        """The content type this serializer produces (e.g., 'application/json')."""
        pass

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """
        Serialize Python data to bytes.

        Args:
            data: The data to serialize

        Returns:
            The serialized bytes

        Raises:
            ValidationError: If the data cannot be serialized
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes, target_type: Type[T]) -> T:
        """
        Deserialize bytes to a Python object.

        Args:
            data: The bytes to deserialize
            target_type: The expected type of the result

        Returns:
            The deserialized object

        Raises:
            ValidationError: If the data cannot be deserialized
        """
        pass


class SerializerRegistry:
    """Registry for managing available serializers."""

    def __init__(self) -> None:
        self._serializers: dict[str, Serializer] = {}
        self._content_type_map: dict[str, Serializer] = {}

    def register(self, name: str, serializer: Serializer) -> None:
        """
        Register a serializer.

        Args:
            name: The name to register the serializer under
            serializer: The serializer instance
        """
        self._serializers[name] = serializer
        self._content_type_map[serializer.content_type] = serializer

    def get(self, name: str) -> Serializer:
        """
        Get a serializer by name.

        Args:
            name: The serializer name

        Returns:
            The serializer instance

        Raises:
            KeyError: If the serializer is not found
        """
        return self._serializers[name]

    def get_by_content_type(self, content_type: str) -> Serializer:
        """
        Get a serializer by content type.

        Args:
            content_type: The content type (e.g., 'application/json')

        Returns:
            The serializer instance

        Raises:
            KeyError: If no serializer handles this content type
        """
        return self._content_type_map[content_type]

    def list_serializers(self) -> list[str]:
        """List all registered serializer names."""
        return list(self._serializers.keys())

    def list_content_types(self) -> list[str]:
        """List all supported content types."""
        return list(self._content_type_map.keys())


# Global serializer registry
_registry = SerializerRegistry()


def register_serializer(name: str, serializer: Serializer) -> None:
    """Register a serializer in the global registry."""
    _registry.register(name, serializer)


def get_serializer(name: str) -> Serializer:
    """Get a serializer from the global registry."""
    return _registry.get(name)


def get_serializer_by_content_type(content_type: str) -> Serializer:
    """Get a serializer by content type from the global registry."""
    return _registry.get_by_content_type(content_type)
