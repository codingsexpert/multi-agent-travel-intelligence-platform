"""Safe Mock/Demo Transactional Providers for Travel Actions.

These providers simulate external transactional booking systems for flights, hotels,
and activities. In accordance with platform safety and HITL principles:
- They NEVER perform real external financial transactions or real reservations.
- Every response is explicitly marked 'DEMO / MOCK'.
- They support simulating successes, business errors, cancellations, and timeouts.
- Designed with clean interfaces to allow swapping with real providers in the future.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("travel_platform.mcp.transactional")


class TransactionalProviderError(Exception):
    """Base exception for transactional provider failures."""
    pass


class ProviderTimeoutError(TransactionalProviderError):
    """Simulated provider timeout exception."""
    pass


class MockFlightBookingProvider:
    """Safe Mock Provider for flight bookings and cancellations.
    
    All bookings are purely synthetic demo records.
    """

    def __init__(self, simulate_timeout: bool = False, simulate_failure: bool = False):
        self.simulate_timeout = simulate_timeout
        self.simulate_failure = simulate_failure

    def book_flight(
        self,
        flight_number: str,
        passenger_name: str,
        departure_date: str,
        origin: str,
        destination: str,
        seat_class: str = "Economy",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate flight booking."""
        if self.simulate_timeout:
            logger.warning("[MOCK FLIGHT PROVIDER] Simulating timeout")
            raise ProviderTimeoutError("Simulated airline GDS timeout after 30s")

        if self.simulate_failure:
            logger.warning("[MOCK FLIGHT PROVIDER] Simulating inventory exhaustion")
            raise TransactionalProviderError("Airline inventory exhausted for flight: " + flight_number)

        pnr = f"DEMO-FLT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK FLIGHT GDS",
            "confirmation_code": pnr,
            "status": "CONFIRMED",
            "flight_number": flight_number,
            "passenger_name": passenger_name,
            "departure_date": departure_date,
            "route": f"{origin} -> {destination}",
            "seat_class": seat_class,
            "idempotency_key": idempotency_key,
            "booked_at": datetime.now(timezone.utc).isoformat(),
            "notes": "SIMULATED BOOKING - NO REAL TICKET ISSUED",
        }

    def cancel_flight(
        self,
        confirmation_code: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate flight cancellation."""
        if self.simulate_failure:
            raise TransactionalProviderError("Cancellation rejected by simulated airline policy.")

        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK FLIGHT GDS",
            "confirmation_code": confirmation_code,
            "status": "CANCELLED",
            "refund_status": "MOCK_REFUND_INITIATED",
            "reason": reason or "User requested cancellation",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }


class MockHotelBookingProvider:
    """Safe Mock Provider for hotel reservations."""

    def __init__(self, simulate_timeout: bool = False, simulate_failure: bool = False):
        self.simulate_timeout = simulate_timeout
        self.simulate_failure = simulate_failure

    def book_hotel(
        self,
        hotel_name: str,
        guest_name: str,
        check_in: str,
        check_out: str,
        room_type: str = "Standard Room",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate hotel room reservation."""
        if self.simulate_timeout:
            raise ProviderTimeoutError("Simulated hotel reservation system timeout")

        if self.simulate_failure:
            raise TransactionalProviderError("Hotel has no availability for requested dates: " + hotel_name)

        confirmation_code = f"DEMO-HTL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK HOTEL CRS",
            "confirmation_code": confirmation_code,
            "status": "CONFIRMED",
            "hotel_name": hotel_name,
            "guest_name": guest_name,
            "check_in": check_in,
            "check_out": check_out,
            "room_type": room_type,
            "idempotency_key": idempotency_key,
            "booked_at": datetime.now(timezone.utc).isoformat(),
            "notes": "SIMULATED RESERVATION - NO PAYMENT CHARGED",
        }

    def cancel_hotel(
        self,
        confirmation_code: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate hotel cancellation."""
        if self.simulate_failure:
            raise TransactionalProviderError("Non-refundable room cancellation rejected.")

        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK HOTEL CRS",
            "confirmation_code": confirmation_code,
            "status": "CANCELLED",
            "refund_status": "MOCK_REFUND_INITIATED",
            "reason": reason or "User requested cancellation",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }


class MockActivityBookingProvider:
    """Safe Mock Provider for tours, tickets, and activities."""

    def __init__(self, simulate_timeout: bool = False, simulate_failure: bool = False):
        self.simulate_timeout = simulate_timeout
        self.simulate_failure = simulate_failure

    def book_activity(
        self,
        activity_title: str,
        participant_name: str,
        activity_date: str,
        tickets_count: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate activity booking / voucher issuance."""
        if self.simulate_timeout:
            raise ProviderTimeoutError("Simulated activity ticketing gateway timeout")

        if self.simulate_failure:
            raise TransactionalProviderError("Activity slots sold out: " + activity_title)

        voucher_code = f"DEMO-ACT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK ACTIVITY TICKETING",
            "confirmation_code": voucher_code,
            "status": "CONFIRMED",
            "activity_title": activity_title,
            "participant_name": participant_name,
            "activity_date": activity_date,
            "tickets_count": tickets_count,
            "idempotency_key": idempotency_key,
            "booked_at": datetime.now(timezone.utc).isoformat(),
            "notes": "SIMULATED TICKET VOUCHER - ZERO MONETARY VALUE",
        }

    def cancel_activity(
        self,
        confirmation_code: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate activity ticket cancellation."""
        if self.simulate_failure:
            raise TransactionalProviderError("Voucher non-cancellable within 24h window.")

        return {
            "is_mock": True,
            "provider_type": "DEMO / MOCK ACTIVITY TICKETING",
            "confirmation_code": confirmation_code,
            "status": "CANCELLED",
            "refund_status": "MOCK_REFUND_PROCESSED",
            "reason": reason or "User cancellation",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }
