"""The Goal Zero Yeti integration."""
import asyncio
from datetime import timedelta
from logging import getLogger

from goalzero import Yeti, exceptions

from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_IDENTIFIERS,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_SW_VERSION,
    DATA_KEY_API,
    DATA_KEY_COORDINATOR,
    DOMAIN,
)

_LOGGER = getLogger(__name__)


PLATFORMS = [DOMAIN_BINARY_SENSOR, DOMAIN_SENSOR, DOMAIN_SWITCH]


async def async_setup(hass: HomeAssistant, config):
    """Set up the Goal Zero Yeti component."""
    hass.data[DOMAIN] = {}

    return True


async def async_setup_entry(hass, entry):
    """Set up Goal Zero Yeti from a config entry."""
    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    session = async_get_clientsession(hass)
    api = Yeti(host, hass.loop, session)
    try:
        await api.init_connect()
    except exceptions.ConnectError as ex:
        _LOGGER.warning("Failed to connect: %s", ex)
        raise ConfigEntryNotReady from ex

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            await api.get_state()
        except exceptions.ConnectError as err:
            raise UpdateFailed("Failed to communicate with device") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=name,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_KEY_API: api,
        DATA_KEY_COORDINATOR: coordinator,
    }

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
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class YetiEntity(CoordinatorEntity):
    """Representation of a Goal Zero Yeti entity."""

    def __init__(self, api, coordinator, name, server_unique_id):
        """Initialize a Goal Zero Yeti entity."""
        super().__init__(coordinator)
        self.api = api
        self._name = name
        self._server_unique_id = server_unique_id
        self._device_class = None
        self.sw_version = None
        self.model = None

    @property
    def device_info(self):
        """Return the device information of the entity."""
        if self.api.data:
            self.sw_version = self.api.data["firmwareVersion"]
        if self.api.sysdata:
            self.model = self.api.sysdata["model"]
        return {
            CONF_IDENTIFIERS: {(DOMAIN, self._server_unique_id)},
            CONF_MANUFACTURER: "Goal Zero",
            CONF_MODEL: self.model,
            CONF_NAME: self._name,
            CONF_SW_VERSION: self.sw_version,
        }

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._device_class
