#!/usr/bin/env python3
"""
Simple example demonstrating Travessera usage.

This example shows how to use Travessera to interact with a mock user API.
"""

import asyncio

from pydantic import BaseModel

from travessera import ApiKeyAuthentication, Service, Travessera
from travessera.exceptions import NotFoundError


# Define your data models
class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True


class UserCreate(BaseModel):
    name: str
    email: str


# Configure the service
def setup_travessera():
    """Set up Travessera with a user service."""
    # In a real application, you'd get the API key from environment variables
    auth = ApiKeyAuthentication(api_key="demo-api-key")

    user_service = Service(
        name="users",
        base_url="https://jsonplaceholder.typicode.com",  # Example API
        timeout=30,
        authentication=auth,
    )

    return Travessera(
        services=[user_service], default_headers={"X-Client": "travessera-demo"}
    )


# Initialize Travessera
travessera = setup_travessera()


# Define your endpoints
@travessera.get("users", "/users/{user_id}")
async def get_user(user_id: int) -> dict:
    """Get a user by ID."""
    pass


@travessera.get("users", "/users")
async def list_users(limit: int | None = None) -> list[dict]:
    """List all users."""
    pass


@travessera.post("users", "/users")
async def create_user(user: UserCreate) -> dict:
    """Create a new user."""
    pass


# Synchronous versions (Travessera supports both!)
@travessera.get("users", "/users/{user_id}")
def get_user_sync(user_id: int) -> dict:
    """Get a user by ID (synchronous version)."""
    pass


async def async_example():
    """Demonstrate async usage."""
    print("=== Async Example ===")

    try:
        # Get a specific user
        user = await get_user(1)
        print(f"User 1: {user['name']} ({user['email']})")

        # List users
        users = await list_users(limit=3)
        print(f"\nFound {len(users)} users:")
        for u in users[:3]:
            print(f"  - {u['name']}")

        # Create a user (note: jsonplaceholder doesn't actually create, just simulates)
        new_user = await create_user(
            UserCreate(name="Jane Doe", email="jane@travessera.example")
        )
        print(f"\nCreated user with ID: {new_user['id']}")

        # Handle errors
        try:
            await get_user(999999)  # Non-existent user
        except NotFoundError:
            print("\nUser 999999 not found (as expected)")

    except Exception as e:
        print(f"Error: {e}")


def sync_example():
    """Demonstrate synchronous usage."""
    print("\n=== Sync Example ===")

    try:
        # Synchronous call
        user = get_user_sync(2)
        print(f"User 2: {user['name']} ({user['email']})")

    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run examples."""
    print("Travessera Simple Example")
    print("=" * 50)

    # Use async context manager to ensure proper cleanup
    async with travessera:
        # Run async example
        await async_example()

        # Run sync example
        sync_example()

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
