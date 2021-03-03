"""Config flow for Goal Zero Yeti integration."""
from goalzero import Yeti, exceptions
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.dhcp import IP_ADDRESS, MAC_ADDRESS
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import _LOGGER
from .const import DEFAULT_NAME
from .const import DOMAIN  # pylint:disable=unused-import

DATA_SCHEMA = vol.Schema({"host": str, "name": str})


class GoalZeroFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Goal Zero Yeti."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the goalzero flow."""
        self.ip_address = None

    async def async_step_dhcp(self, dhcp_discovery):
        """Handle dhcp discovery."""
        self.ip_address = dhcp_discovery[IP_ADDRESS]
        for entry in self._async_current_entries():
            CONF_DATA = {
                CONF_HOST: self.ip_address,
                CONF_NAME: entry.data.get(CONF_NAME),
                CONF_SCAN_INTERVAL: entry.data.get(CONF_SCAN_INTERVAL),
                CONF_MAC: dhcp_discovery[MAC_ADDRESS],
            }
            if entry.data.get(CONF_HOST) == self.ip_address:
                return self.async_abort(reason="already_configured")
            elif entry.data.get(CONF_HOST) != self.ip_address and (
                entry.data.get(CONF_MAC) is None
                or entry.data.get(CONF_MAC) == dhcp_discovery[MAC_ADDRESS]
            ):
                self.hass.config_entries.async_update_entry(entry, data=CONF_DATA)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="already_configured")
        # pylint: disable=no-member # https://github.com/PyCQA/pylint/issues/3167
        self.context["title_placeholders"] = {CONF_HOST: self.ip_address}
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input[CONF_NAME]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            # await self.async_set_unique_id(host)
            # self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                api = Yeti(host, self.hass.loop, session)
                await api.init_connect()
                for entry in self._async_current_entries():
                    _LOGGER.error(entry.data)
                    if entry.data.get(CONF_HOST) == host:
                        return self.async_abort(reason="already_configured")
                    elif entry.data.get(CONF_HOST) != self.ip_address and (
                        entry.data.get(CONF_MAC) is None
                        or entry.data.get(CONF_MAC) == api.sysdata["macAddress"]
                    ):
                        _LOGGER.error(entry.data)
                        CONF_DATA = {
                            CONF_HOST: host,
                            CONF_NAME: name,
                            CONF_SCAN_INTERVAL: scan_interval,
                            CONF_MAC: api.sysdata["macAddress"],
                        }
                        self.hass.config_entries.async_update_entry(
                            entry, data=CONF_DATA
                        )
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="already_configured")
                        # await self.async_set_unique_id(entry.data.get(CONF_HOST))
                        # self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                        # break
            except exceptions.ConnectError:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Error connecting to device at %s", host)
            except exceptions.InvalidHost:
                errors["base"] = "invalid_host"
                _LOGGER.error("Invalid host at %s", host)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: host,
                        CONF_NAME: name,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_MAC: api.sysdata["macAddress"],
                    },
                )

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.ip_address): str,
                    vol.Optional(
                        CONF_NAME, default=user_input.get(CONF_NAME) or DEFAULT_NAME
                    ): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=30): vol.All(
                        vol.Coerce(int), vol.Clamp(min=5, max=600)
                    ),
                }
            ),
            errors=errors,
        )

    @callback
    def _async_ip_address_already_configured(self, ip_address):
        """See if we already have an entry matching the ip_address."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_HOST) == ip_address:
                return True
        return False
