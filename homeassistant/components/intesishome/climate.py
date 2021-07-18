"""Support for IntesisHome and airconwithme Smart AC Controllers."""
import logging
from random import randrange

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_DEVICE,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later

_LOGGER = logging.getLogger(__name__)

IH_DEVICE_INTESISHOME = "IntesisHome"
IH_DEVICE_AIRCONWITHME = "airconwithme"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_DEVICE, default=IH_DEVICE_INTESISHOME): vol.In(
            [IH_DEVICE_AIRCONWITHME, IH_DEVICE_INTESISHOME]
        ),
    }
)

MAP_IH_TO_HVAC_MODE = {
    "auto": HVAC_MODE_HEAT_COOL,
    "cool": HVAC_MODE_COOL,
    "dry": HVAC_MODE_DRY,
    "fan": HVAC_MODE_FAN_ONLY,
    "heat": HVAC_MODE_HEAT,
    "off": HVAC_MODE_OFF,
}
MAP_HVAC_MODE_TO_IH = {v: k for k, v in MAP_IH_TO_HVAC_MODE.items()}

MAP_IH_TO_PRESET_MODE = {
    "eco": PRESET_ECO,
    "comfort": PRESET_COMFORT,
    "powerful": PRESET_BOOST,
}
MAP_PRESET_MODE_TO_IH = {v: k for k, v in MAP_IH_TO_PRESET_MODE.items()}

IH_SWING_STOP = "auto/stop"
IH_SWING_SWING = "swing"
MAP_SWING_TO_IH = {
    SWING_OFF: {"vvane": IH_SWING_STOP, "hvane": IH_SWING_STOP},
    SWING_BOTH: {"vvane": IH_SWING_SWING, "hvane": IH_SWING_SWING},
    SWING_HORIZONTAL: {"vvane": IH_SWING_STOP, "hvane": IH_SWING_SWING},
    SWING_VERTICAL: {"vvane": IH_SWING_SWING, "hvane": IH_SWING_STOP},
}


MAP_STATE_ICONS = {
    HVAC_MODE_COOL: "mdi:snowflake",
    HVAC_MODE_DRY: "mdi:water-off",
    HVAC_MODE_FAN_ONLY: "mdi:fan",
    HVAC_MODE_HEAT: "mdi:white-balance-sunny",
    HVAC_MODE_HEAT_COOL: "mdi:cached",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Create the IntesisHome climate devices."""
    ih_user = config[CONF_USERNAME]
    ih_pass = config[CONF_PASSWORD]
    device_type = config[CONF_DEVICE]

    controller = IntesisHome(
        ih_user,
        ih_pass,
        hass.loop,
        websession=async_get_clientsession(hass),
        device_type=device_type,
    )
    try:
        await controller.poll_status()
    except IHAuthenticationError:
        _LOGGER.error("Invalid username or password")
        return
    except IHConnectionError as ex:
        _LOGGER.error("Error connecting to the %s server", device_type)
        raise PlatformNotReady from ex

    ih_devices = controller.get_devices()
    if ih_devices:
        async_add_entities(
            [
                IntesisAC(ih_device_id, device, controller)
                for ih_device_id, device in ih_devices.items()
            ],
            True,
        )
    else:
        _LOGGER.error(
            "Error getting device list from %s API: %s",
            device_type,
            controller.error_message,
        )
        await controller.stop()


class IntesisAC(ClimateEntity):
    """Represents an Intesishome air conditioning device."""

    _attr_preset_modes = [PRESET_ECO, PRESET_COMFORT, PRESET_BOOST]
    _attr_should_poll = False
    _attr_swing_modes = [SWING_OFF]
    _attr_target_temperature_step = 1
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, ih_device_id, ih_device, controller):
        """Initialize the thermostat."""
        self._controller = controller
        self._attr_unique_id = ih_device_id
        self._ih_device = ih_device
        self._attr_name = ih_device.get("name")
        self._device_type = controller.device_type
        self._attr_available = True
        self._attr_hvac_modes = []
        self._attr_supported_features = 0

        # Setpoint support
        if controller.has_setpoint_control(ih_device_id):
            self._attr_supported_features |= SUPPORT_TARGET_TEMPERATURE

        # Setup swing list
        if controller.has_vertical_swing(ih_device_id):
            self._attr_swing_modes.append(SWING_VERTICAL)
        if controller.has_horizontal_swing(ih_device_id):
            self._attr_swing_modes.append(SWING_HORIZONTAL)
        if SWING_HORIZONTAL in self.swing_modes and SWING_VERTICAL in self.swing_modes:
            self._attr_swing_modes.append(SWING_BOTH)
        if len(self.swing_modes) > 1:
            self._attr_supported_features |= SUPPORT_SWING_MODE

        # Setup fan speeds
        self._attr_fan_modes = controller.get_fan_speed_list(ih_device_id)
        if self.fan_modes:
            self._attr_supported_features |= SUPPORT_FAN_MODE

        # Preset support
        if ih_device.get("climate_working_mode"):
            self._attr_supported_features |= SUPPORT_PRESET_MODE

        # Setup HVAC modes
        modes = controller.get_mode_list(ih_device_id)
        if modes:
            mode_list = [MAP_IH_TO_HVAC_MODE[mode] for mode in modes]
            self._attr_hvac_modes.extend(mode_list)
        self._attr_hvac_modes.append(HVAC_MODE_OFF)

    async def async_added_to_hass(self):
        """Subscribe to event updates."""
        _LOGGER.debug("Added climate device with state: %s", repr(self._ih_device))
        await self._controller.add_update_callback(self.async_update_callback)
        try:
            await self._controller.connect()
        except IHConnectionError as ex:
            _LOGGER.error("Exception connecting to IntesisHome: %s", ex)
            raise PlatformNotReady from ex

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)

        if hvac_mode:
            await self.async_set_hvac_mode(hvac_mode)

        if temperature:
            _LOGGER.debug("Setting %s to %s degrees", self._device_type, temperature)
            await self._controller.set_temperature(self.unique_id, temperature)
            self._attr_target_temperature = temperature

        # Write updated temperature to HA state to avoid flapping (API confirmation is slow)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        _LOGGER.debug("Setting %s to %s mode", self._device_type, hvac_mode)
        if hvac_mode == HVAC_MODE_OFF:
            self._attr_icon = None
            self._attr_hvac_mode = HVAC_MODE_OFF
            await self._controller.set_power_off(self.unique_id)
            # Write changes to HA, API can be slow to push changes
            self.async_write_ha_state()
            return

        # First check device is turned on
        if not self._controller.is_on(self.unique_id):
            self._attr_icon = MAP_STATE_ICONS.get(hvac_mode)
            await self._controller.set_power_on(self.unique_id)

        # Set the mode
        await self._controller.set_mode(self.unique_id, MAP_HVAC_MODE_TO_IH[hvac_mode])

        # Send the temperature again in case changing modes has changed it
        if self.target_temperature:
            await self._controller.set_temperature(
                self.unique_id, self.target_temperature
            )

        # Updates can take longer than 2 seconds, so update locally
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode (from quiet, low, medium, high, auto)."""
        await self._controller.set_fan_speed(self.unique_id, fan_mode)

        # Updates can take longer than 2 seconds, so update locally
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        """Set preset mode."""
        ih_preset_mode = MAP_PRESET_MODE_TO_IH.get(preset_mode)
        await self._controller.set_preset_mode(self.unique_id, ih_preset_mode)

    async def async_set_swing_mode(self, swing_mode):
        """Set the vertical vane."""
        swing_settings = MAP_SWING_TO_IH.get(swing_mode)
        if swing_settings:
            await self._controller.set_vertical_vane(
                self.unique_id, swing_settings.get("vvane")
            )
            await self._controller.set_horizontal_vane(
                self.unique_id, swing_settings.get("hvane")
            )

    async def async_update(self):
        """Copy values from controller dictionary to climate device."""
        # Update values from controller's device dictionary
        self._attr_available = self._controller.is_connected
        self._attr_current_temperature = self._controller.get_temperature(
            self.unique_id
        )
        self._attr_fan_mode = self._controller.get_fan_speed(self.unique_id)
        self._attr_min_temp = self._controller.get_min_setpoint(self.unique_id)
        self._attr_max_temp = self._controller.get_max_setpoint(self.unique_id)
        self._attr_target_temperature = self._controller.get_setpoint(self.unique_id)
        outdoor_temp = self._controller.get_outdoor_temperature(self.unique_id)

        self._attr_icon = None
        self._attr_hvac_mode = HVAC_MODE_OFF
        if self._controller.is_on(self.unique_id):
            mode = self._controller.get_mode(self.unique_id)
            self._attr_hvac_mode = MAP_IH_TO_HVAC_MODE.get(mode)
            self._attr_icon = MAP_STATE_ICONS.get(self.hvac_mode)

        # Preset mode
        preset = self._controller.get_preset_mode(self.unique_id)
        self._attr_preset_mode = MAP_IH_TO_PRESET_MODE.get(preset)

        # Swing mode
        # Climate module only supports one swing setting.
        vvane = self._controller.get_vertical_swing(self.unique_id)
        hvane = self._controller.get_horizontal_swing(self.unique_id)
        if vvane == IH_SWING_SWING and hvane == IH_SWING_SWING:
            swing = SWING_BOTH
        elif vvane == IH_SWING_SWING:
            swing = SWING_VERTICAL
        elif hvane == IH_SWING_SWING:
            swing = SWING_HORIZONTAL
        else:
            swing = SWING_OFF
        self._attr_swing_mode = swing

        # Power usage
        power_consumption_heat = self._controller.get_heat_power_consumption(
            self.unique_id
        )
        power_consumption_cool = self._controller.get_cool_power_consumption(
            self.unique_id
        )
        self._attr_extra_state_attributes = {}
        if outdoor_temp:
            self._attr_extra_state_attributes["outdoor_temp"] = outdoor_temp
        if power_consumption_heat:
            self._attr_extra_state_attributes["power_consumption_heat_kw"] = round(
                power_consumption_heat / 1000, 1
            )
        if power_consumption_cool:
            self._attr_extra_state_attributes["power_consumption_cool_kw"] = round(
                power_consumption_cool / 1000, 1
            )

    async def async_will_remove_from_hass(self):
        """Shutdown the controller when the device is being removed."""
        await self._controller.stop()

    async def async_update_callback(self, device_id=None):
        """Let HA know there has been an update from the controller."""
        # Track changes in connection state
        if not self._controller.is_connected and self.available:
            # Connection has dropped
            self._attr_available = False
            reconnect_minutes = 1 + randrange(10)
            _LOGGER.error(
                "Connection to %s API was lost. Reconnecting in %i minutes",
                self._device_type,
                reconnect_minutes,
            )
            # Schedule reconnection

            async def try_connect(_now):
                await self._controller.connect()

            async_call_later(self.hass, reconnect_minutes * 60, try_connect)

        if self._controller.is_connected and not self.available:
            # Connection has been restored
            self._attr_available = True
            _LOGGER.debug("Connection to %s API was restored", self._device_type)

        if not device_id or self.unique_id == device_id:
            # Update all devices if no device_id was specified
            _LOGGER.debug(
                "%s API sent a status update for device %s",
                self._device_type,
                device_id,
            )
            self.async_schedule_update_ha_state(True)
