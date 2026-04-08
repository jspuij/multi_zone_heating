"""Fixtures for the multi_zone_heating integration tests."""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntryState

from custom_components.multi_zone_heating.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in tests."""


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={},
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
