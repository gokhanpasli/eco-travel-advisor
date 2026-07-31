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
    ActionSelectTransportOption,
    island_ferry_legs,
    island_ferry_options,
    estimate_travel_minutes,
    generated_accommodation_options,
    normalise_transport_mode,
    transport_base_mode,
    usable_port_name,
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
            "text": "",
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


def test_island_offers_every_sailing_port():
    """Each port that actually serves the island is offered."""
    options = island_ferry_options("Berlin", "Mallorca")
    ports = {option["via"] for option in options}

    assert ports == {"Barcelona", "Valencia", "Denia"}, (
        "Alicante and Malaga have no Mallorca sailing and must not appear"
    )


def test_ferry_ports_are_ordered_by_land_distance():
    """The shortest land leg is offered first."""
    options = island_ferry_options("Berlin", "Mallorca")
    distances = [option["land_distance_km"] for option in options]

    assert distances == sorted(distances)


def test_mainland_route_offers_no_sailings():
    assert island_ferry_options("Berlin", "Rome") == []


def test_mode_name_keeps_its_port_readable():
    """Title-casing the whole name used to produce "Train Via Barcelona"."""
    assert normalise_transport_mode("train via barcelona") == "Train via Barcelona"
    assert normalise_transport_mode("TRAIN VIA DENIA") == "Train via Denia"
    assert normalise_transport_mode("flight") == "Flight"


def test_base_mode_ignores_the_port():
    assert transport_base_mode("Train via Barcelona") == "Train"
    assert transport_base_mode("Bus via Denia") == "Bus"
    assert transport_base_mode("Flight") == "Flight"


def test_ferry_variant_can_be_selected():
    """Selecting a port variant was rejected as an unknown mode."""
    text, slots, _ = run_action(
        ActionSelectTransportOption(),
        dict(TRIP_SLOTS, ferry_preference="accepted"),
        intent="select_transport_option",
        entities=[{
            "entity": "selected_transport_mode",
            "value": "Train via Barcelona",
        }],
    )

    assert "choose one of the transport cards" not in text.lower()
    assert slots["selected_transport_mode"] == "Train via Barcelona"


def test_unknown_mode_is_still_rejected():
    text, _, _ = run_action(
        ActionSelectTransportOption(),
        TRIP_SLOTS,
        intent="select_transport_option",
        entities=[{
            "entity": "selected_transport_mode",
            "value": "Teleport",
        }],
    )

    assert "choose one of the transport cards" in text.lower()


def test_ireland_needs_a_crossing_too():
    """Dublin had the same gap Mallorca did: no land route exists."""
    options = island_ferry_options("Berlin", "Dublin")

    assert options, "Ireland is an island and needs a ferry leg"
    assert {"Holyhead", "Liverpool", "Cherbourg"} == {
        option["via"] for option in options
    }


def test_london_needs_no_crossing():
    """The Channel Tunnel carries trains, so Britain is not cut off."""
    assert island_ferry_options("Berlin", "London") == []


def test_generated_stays_follow_the_city_price_level():
    """Every uncurated city used to return the same single stay."""
    zurich = generated_accommodation_options("Zurich")
    istanbul = generated_accommodation_options("Istanbul")

    assert len(zurich) > 1, "a city should offer more than one stay"
    assert zurich[0]["price"] > istanbul[0]["price"], (
        "Zurich is a more expensive city than Istanbul"
    )
    assert "Zurich" in zurich[0]["name"]


def test_travel_time_ranks_the_modes_sensibly():
    """A flight beats a train, and a train beats a bus, over distance."""
    flight = estimate_travel_minutes("Flight", 1500)
    train = estimate_travel_minutes("Train", 1500)
    bus = estimate_travel_minutes("Bus", 1500)

    assert flight < train < bus


def test_short_hops_carry_their_fixed_overhead():
    """Check-in and transfers dominate a very short flight."""
    assert estimate_travel_minutes("Flight", 0) >= 120


ROUTED_ISLAND_JOURNEY = {
    "has_ferry": True,
    "road_distance_km": 2200.0,
    "ferry_distance_km": 106.0,
    "ferry_duration_minutes": 150,
    "ferry_route_name": "Denia to Ibiza",
    "ferry_departure_port": "Denia",
    "ferry_arrival_port": "Ibiza",
}


def test_uncurated_island_is_detected_from_the_route():
    """Any island works without being listed by hand."""
    options = island_ferry_options(
        "Berlin",
        "Ibiza",
        ROUTED_ISLAND_JOURNEY,
    )

    assert len(options) == 1
    assert options[0]["ferry_distance_km"] == 106.0
    assert options[0]["via"] == "Denia"


def test_curated_sailings_win_over_the_routed_one():
    """Curated data can compare ports, so it takes precedence."""
    options = island_ferry_options(
        "Berlin",
        "Mallorca",
        ROUTED_ISLAND_JOURNEY,
    )

    assert len(options) > 1
    assert {"Barcelona", "Valencia", "Denia"} == {
        option["via"] for option in options
    }


def test_a_routed_journey_without_a_ferry_stays_mainland():
    assert island_ferry_options(
        "Berlin",
        "Rome",
        {"has_ferry": False, "road_distance_km": 1500.0},
    ) == []


def test_generic_ferry_names_do_not_become_a_port():
    """"Train via Vehicle ferry segment" would read as nonsense."""
    assert usable_port_name("Vehicle ferry segment") is None
    assert usable_port_name("") is None
    assert usable_port_name("Denia") == "Denia"


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
