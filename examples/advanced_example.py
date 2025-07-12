#!/usr/bin/env python3
"""
Advanced example demonstrating Travessera's advanced features.

This example shows:
- Multiple services
- Custom error handling
- Request/response transformers
- Dynamic headers
- Retry configuration
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from travessera import (
    ApiKeyAuthentication,
    BearerTokenAuthentication,
    Service,
    Travessera,
)
from travessera.exceptions import NetworkError, ServerError
from travessera.models import RetryConfig


# Custom exceptions
class UserNotFound(Exception):
    """Raised when a user is not found."""

    pass


class OrderNotFound(Exception):
    """Raised when an order is not found."""

    pass


# Data models
class User(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class Order(BaseModel):
    id: int
    user_id: int
    items: List[str]
    total: float
    status: str = "pending"


class Payment(BaseModel):
    order_id: int
    amount: float
    method: str = "credit_card"


class PaymentResult(BaseModel):
    transaction_id: str
    status: str
    timestamp: datetime


# Set up multiple services
def setup_services():
    """Configure multiple microservices."""
    # User service with API key auth
    user_service = Service(
        name="users",
        base_url="https://api.users.example.com",
        timeout=30,
        authentication=ApiKeyAuthentication(api_key="user-service-key"),
        headers={"X-Service-Version": "2.0"},
    )

    # Order service with bearer token auth
    order_service = Service(
        name="orders",
        base_url="https://api.orders.example.com",
        timeout=45,
        authentication=BearerTokenAuthentication(token="order-service-token"),
        retry_config=RetryConfig(
            max_attempts=5,
            min_wait=2.0,
            max_wait=30.0,
            retry_on=(NetworkError, ServerError),
        ),
    )

    # Payment service with custom retry config
    payment_service = Service(
        name="payments",
        base_url="https://api.payments.example.com",
        timeout=60,
        authentication=ApiKeyAuthentication(
            api_key="payment-key", header_name="X-Payment-API-Key"
        ),
        retry_config=RetryConfig(
            max_attempts=3,
            min_wait=5.0,  # Payments need longer wait times
            max_wait=60.0,
        ),
    )

    return Travessera(
        services=[user_service, order_service, payment_service],
        default_headers={
            "X-Client": "travessera-advanced-demo",
            "X-Request-ID": str(uuid.uuid4()),
        },
    )


# Initialize Travessera
travessera = setup_services()


# User service endpoints with custom error mapping
@travessera.get(
    "users",
    "/users/{user_id}",
    raises={404: UserNotFound},
    headers_factory=lambda params: {
        "X-User-Request": str(params["user_id"]),
        "X-Timestamp": datetime.now().isoformat(),
    },
)
async def get_user(user_id: int) -> User:
    """Get user with custom error handling and dynamic headers."""
    pass


# Order service with request transformation
@travessera.post(
    "orders",
    "/orders",
    request_transformer=lambda data: {
        "order_data": data,
        "metadata": {
            "source": "travessera",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
        },
    },
)
async def create_order(order: Order) -> Order:
    """Create order with request transformation."""
    pass


# Order service with response transformation
@travessera.get(
    "orders",
    "/orders/{order_id}",
    response_transformer=lambda resp: resp.get("data", {}).get("order", {}),
    raises={404: OrderNotFound},
)
async def get_order(order_id: int) -> Order:
    """Get order with response transformation."""
    pass


# Payment service with comprehensive configuration
@travessera.post(
    "payments",
    "/process",
    timeout=120.0,  # Override service timeout for payments
    retry_config=RetryConfig(
        max_attempts=3,
        min_wait=10.0,
        max_wait=60.0,
    ),
    headers={
        "X-Payment-Priority": "high",
        "X-Idempotency-Key": str(uuid.uuid4()),
    },
    headers_factory=lambda params: {
        "X-Order-ID": str(params.get("order_id", "unknown")),
        "X-Amount": str(params.get("amount", 0)),
    },
)
async def process_payment(payment: Payment) -> PaymentResult:
    """Process payment with custom retry and headers."""
    pass


# Batch operations with pagination
@travessera.get(
    "users",
    "/users",
    headers={"X-Batch-Operation": "true"},
)
async def list_users(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    created_after: Optional[datetime] = None,
) -> List[User]:
    """List users with complex query parameters."""
    pass


# Demonstrate chaining multiple service calls
async def complete_purchase_flow(user_id: int, items: List[str], amount: float):
    """
    Complete purchase flow across multiple services.

    This demonstrates how Travessera makes it easy to orchestrate
    calls across multiple microservices.
    """
    try:
        # 1. Verify user exists
        user = await get_user(user_id)
        print(f"Processing order for user: {user.name}")

        # 2. Create order
        order = Order(
            id=0,  # Will be assigned by service
            user_id=user_id,
            items=items,
            total=amount,
        )
        created_order = await create_order(order)
        print(f"Created order {created_order.id} with status: {created_order.status}")

        # 3. Process payment
        payment = Payment(
            order_id=created_order.id,
            amount=amount,
            method="credit_card",
        )
        payment_result = await process_payment(payment)
        print(
            f"Payment {payment_result.transaction_id} status: {payment_result.status}"
        )

        # 4. Verify order status
        final_order = await get_order(created_order.id)
        print(f"Final order status: {final_order.status}")

        return {
            "user": user,
            "order": final_order,
            "payment": payment_result,
        }

    except UserNotFound:
        print(f"User {user_id} not found")
        raise
    except OrderNotFound:
        print("Order not found after creation - possible service issue")
        raise
    except Exception as e:
        print(f"Purchase flow failed: {e}")
        raise


async def demonstrate_batch_operations():
    """Demonstrate batch operations with pagination."""
    print("\n=== Batch Operations ===")

    # Get all active users created in the last month
    recent_users = await list_users(
        page=1,
        per_page=100,
        status="active",
        created_after=datetime.now().replace(day=1),
    )

    print(f"Found {len(recent_users)} recent active users")

    # Process in batches
    batch_size = 10
    for i in range(0, len(recent_users), batch_size):
        batch = recent_users[i : i + batch_size]
        print(f"Processing batch of {len(batch)} users...")
        # Process batch...


async def demonstrate_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n=== Error Handling ===")

    # Test custom error mapping
    try:
        await get_user(99999)
    except UserNotFound:
        print("✓ Custom error mapping worked: UserNotFound")

    # Test network errors with retry
    # In a real scenario, this might succeed after retries
    try:
        # Simulate a flaky endpoint
        await create_order(
            Order(
                id=0,
                user_id=1,
                items=["flaky-item"],
                total=99.99,
            )
        )
    except (NetworkError, ServerError) as e:
        print(f"✓ Network/Server error handled: {type(e).__name__}")


async def main():
    """Run advanced examples."""
    print("Travessera Advanced Example")
    print("=" * 60)

    # Note: These examples won't actually run without real endpoints
    # They demonstrate the API and patterns

    print("\nThis example demonstrates the API patterns.")
    print("In a real application, you would:")
    print("1. Configure real service endpoints")
    print("2. Set up proper authentication")
    print("3. Handle responses from actual services")

    print("\nExample patterns shown:")
    print("- Multiple service configuration")
    print("- Custom error mapping")
    print("- Request/response transformers")
    print("- Dynamic headers")
    print("- Retry configuration")
    print("- Service orchestration")

    # Uncomment these when using real endpoints:
    # await complete_purchase_flow(user_id=123, items=["item1", "item2"], amount=150.00)
    # await demonstrate_batch_operations()
    # await demonstrate_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
