"""Tests for the Goal Zero Yeti integration."""

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.components.dhcp import HOSTNAME, IP_ADDRESS, MAC_ADDRESS
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import DOMAIN, HomeAssistant

from tests.common import MockConfigEntry

HOST = "1.2.3.4"
NAME = "Yeti"

CONF_DATA = {
    CONF_HOST: HOST,
    CONF_NAME: NAME,
}

CONF_CONFIG_FLOW = {
    CONF_HOST: HOST,
    CONF_NAME: NAME,
}

CONF_DHCP_FLOW = {
    IP_ADDRESS: "1.1.1.1",
    MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
    HOSTNAME: "any",
}


async def setup_config_entry(
    hass: HomeAssistant,
    data: dict[str, Any],
    unique_id: str = "any",
) -> bool:
    """Do setup of a MockConfigEntry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=unique_id,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(entry.entry_id)
    return result


async def _create_mocked_yeti(raise_exception=False):
    mocked_yeti = AsyncMock()
    # mocked_yeti.get_state = AsyncMock()
    mocked_yeti.data = {}
    mocked_yeti.data["firmwareVersion"] = "1.0.0"
    mocked_yeti.sysdata = {}
    mocked_yeti.sysdata["model"] = "test_model"
    mocked_yeti.sysdata["macAddress"] = "00:00:00:00:00:00"
    return mocked_yeti


def _patch_init_yeti(mocked_yeti):
    return patch(
        "homeassistant.components.goalzero.Yeti",
        return_value=mocked_yeti,
    )


def _patch_config_flow_yeti(mocked_yeti):
    return patch(
        "homeassistant.components.goalzero.config_flow.Yeti",
        return_value=mocked_yeti,
    )
