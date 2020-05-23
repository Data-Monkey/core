"""The Aurora ABB Powerone PV inverter sensor integration."""

# TODO There is no text for the helpers on the setup screen
# TODO verify that sn, pn, fw read correctly at init.
# TODO remove debug output.
# TODO prevent setting up the integration twice
# TODO default update rate for temperature sensor should be slower.
# TODO (maybe) allow setup via configuration.yaml (deprecated?)

import asyncio
from collections import defaultdict
import logging

from aurorapy.client import AuroraSerialClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Aurora ABB PowerOne component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Aurora ABB PowerOne from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("async_setup_entry got user config data=%s", entry.data)

    comport = entry.data[CONF_PORT]
    address = entry.data[CONF_ADDRESS]
    client = AuroraSerialClient(address, comport, parity="N", timeout=1)
    all_device_params = [
        {"type": "sensor", "parameter": "instantaneouspower", "name": "Power Output"},
        {"type": "sensor", "parameter": "temperature", "name": "Temperature"},
    ]

    entry_data = hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "devices": defaultdict(list),
    }

    entry_data["devices"]["main"] = defaultdict(list)
    for device_params in all_device_params:
        entry_data["devices"]["main"][device_params["type"]].append(device_params)

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    unload_ok = all(
        await asyncio.gather(
            *[
                # hass.config_entries.async_forward_entry_unload(entry, component)
                # for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
