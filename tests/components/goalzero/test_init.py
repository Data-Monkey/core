"""Test Goal Zero integration."""
from unittest.mock import AsyncMock, patch

from goalzero import exceptions

from homeassistant.components.goalzero.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState

from . import CONF_DATA, _patch_init_yeti

from tests.common import MockConfigEntry


async def test_setup_config(hass):
    """Test Goal Zero setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
    )
    entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.goalzero.Yeti.init_connect",
    ):
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    entries = hass.config_entries.async_entries()
    assert entries
    assert len(entries) == 1


async def test_async_setup_entry_not_ready(hass):
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.goalzero.Yeti.init_connect",
        side_effect=exceptions.ConnectError,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_config_entry(hass):
    """Test unload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
    )
    entry.add_to_hass(hass)
    mocked_modem = AsyncMock()
    with _patch_init_yeti(mocked_modem):
        await hass.config_entries.async_setup(entry.entry_id)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(DOMAIN)
