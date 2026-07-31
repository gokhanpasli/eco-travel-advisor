"""Unit tests for the custom action logic.

Run with:  pytest tests/test_actions.py
Requires:  pip install rasa-sdk dateparser requests pytest
"""
import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.actions import (
    ActionCancelDetailChange,
    ActionPrepareDetailChange,
    island_ferry_legs,
)


TRIP_SLOTS = {
    "origin": "Berlin",
    "destination": "Mallorca",
    "trip_type": "business_trip",
    "departure_date": "2026-07-22",
    "return_date": "2026-07-23",
    "budget": 700.0,
    "sustainability_level": "low",
    "selected_transport_mode": None,
    "selected_hotel_name": None,
    "editing_trip_detail": None,
    "trip_change_backup": None,
    "awaiting_trip_confirmation": False,
    "awaiting_detail_confirmation": False,
    "pending_city": None,
    "pending_city_slot": None,
    "fallback_count": 0,
}

SNAPSHOT_FIELDS = (
    "origin",
    "destination",
    "trip_type",
    "departure_date",
    "return_date",
    "budget",
    "sustainability_level",
    "selected_transport_mode",
    "selected_hotel_name",
)


def make_tracker(slots, intent="change_trip_detail", entities=None):
    return Tracker(
        sender_id="test",
        slots=slots,
        latest_message={
            "intent": {"name": intent},
            "entities": entities or [],
        },
        events=[],
        paused=False,
        followup_action=None,
        active_loop={},
        latest_action_name=None,
    )


def run_action(action, slots, **kwargs):
    """Run an action and return (joined bot text, new slots, followup)."""
    dispatcher = CollectingDispatcher()
    tracker = make_tracker(slots, **kwargs)
    events = action.run(dispatcher, tracker, {})

    text = " ".join(m.get("text") or "" for m in dispatcher.messages)
    new_slots = dict(slots)
    followup = None

    for event in events:
        if event.get("event") == "slot":
            new_slots[event["name"]] = event["value"]
        elif event.get("event") == "followup":
            followup = event["name"]

    return text, new_slots, followup


def snapshot_of(slots):
    return {field: slots[field] for field in SNAPSHOT_FIELDS}


def test_change_menu_records_a_backup():
    """Opening the change menu must mark a change flow as active.

    Without this, cancelling from the menu found no backup and wrongly
    reported that there was no active change.
    """
    _, slots, _ = run_action(
        ActionPrepareDetailChange(),
        TRIP_SLOTS,
        entities=[],
    )

    assert slots["trip_change_backup"], (
        "the change menu should snapshot the trip details"
    )


def test_cancel_from_menu_returns_to_transport_options():
    """Cancelling straight from the menu is not a dead end."""
    _, after_menu, _ = run_action(
        ActionPrepareDetailChange(),
        TRIP_SLOTS,
        entities=[],
    )

    text, _, followup = run_action(
        ActionCancelDetailChange(),
        after_menu,
        intent="cancel_change",
    )

    assert "no active change to cancel" not in text.lower()
    assert followup == "action_show_recommendations"


def test_cancel_while_editing_restores_and_reviews():
    """Cancelling a real edit restores the old value and re-reviews."""
    editing = dict(
        TRIP_SLOTS,
        editing_trip_detail="budget",
        budget=None,
        trip_change_backup=snapshot_of(TRIP_SLOTS),
    )

    text, slots, followup = run_action(
        ActionCancelDetailChange(),
        editing,
        intent="cancel_change",
    )

    assert "cancelled" in text.lower()
    assert "Are all these details correct" in text
    assert slots["budget"] == 700.0, "the previous budget should be restored"
    assert followup == "action_listen"


def test_cancel_with_selected_plan_sends_one_message():
    """A selected plan should not produce two stacked 'no changes' lines."""
    with_plan = dict(
        TRIP_SLOTS,
        selected_transport_mode="Train",
        selected_hotel_name="Eco Hotel",
    )
    with_plan["trip_change_backup"] = snapshot_of(with_plan)

    text, _, _ = run_action(
        ActionCancelDetailChange(),
        with_plan,
        intent="cancel_change",
    )

    assert text.lower().count("no changes were made") == 1


def test_island_route_has_a_ferry_leg():
    """A train or bus cannot reach an island without a crossing."""
    legs = island_ferry_legs("Berlin", "Mallorca")

    assert legs is not None, "Mallorca should be treated as an island"
    assert legs["ferry_distance_km"] > 0
    assert legs["land_distance_km"] > 0
    assert "Barcelona" in legs["ferry_departure_port"]
    assert "Palma" in legs["ferry_arrival_port"]


def test_mainland_route_has_no_ferry_leg():
    """Ordinary routes keep the plain point-to-point distance."""
    assert island_ferry_legs("Berlin", "Rome") is None


def test_island_route_is_symmetric():
    """Leaving the island needs the same crossing as arriving."""
    outbound = island_ferry_legs("Berlin", "Mallorca")
    inbound = island_ferry_legs("Mallorca", "Berlin")

    assert inbound is not None
    assert inbound["ferry_distance_km"] == outbound["ferry_distance_km"]


def test_cancel_without_any_context_is_honest():
    """With nothing in progress the assistant still says so plainly."""
    empty = dict(
        TRIP_SLOTS,
        origin=None,
        destination=None,
        trip_change_backup=None,
    )

    text, _, _ = run_action(
        ActionCancelDetailChange(),
        empty,
        intent="cancel_change",
    )

    assert "no active change to cancel" in text.lower()
