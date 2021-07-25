"""Support for LightwaveRF TRVs."""
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    ClimateEntity,
)
from homeassistant.components.climate.const import CURRENT_HVAC_HEAT, CURRENT_HVAC_OFF
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME, TEMP_CELSIUS

from . import CONF_SERIAL, LIGHTWAVE_LINK


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Find and return LightWave lights."""
    if discovery_info is None:
        return

    entities = []
    lwlink = hass.data[LIGHTWAVE_LINK]

    for device_id, device_config in discovery_info.items():
        name = device_config[CONF_NAME]
        serial = device_config[CONF_SERIAL]
        entities.append(LightwaveTrv(name, device_id, lwlink, serial))

    async_add_entities(entities)


class LightwaveTrv(ClimateEntity):
    """Representation of a LightWaveRF TRV."""

    _attr_hvac_mode = HVAC_MODE_HEAT
    _attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
    _attr_max_temp = DEFAULT_MAX_TEMP
    _attr_min_temp = DEFAULT_MIN_TEMP
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, name, device_id, lwlink, serial):
        """Initialize LightwaveTrv entity."""
        self._attr_name = name
        self._device_id = device_id
        self._target_temperature = None
        self._lwlink = lwlink
        self._serial = serial
        self._attr_unique_id = f"{serial}-trv"
        # inhibit is used to prevent race condition on update.  If non zero, skip next update cycle.
        self._inhibit = 0

    def update(self):
        """Communicate with a Lightwave RTF Proxy to get state."""
        (temp, targ, _, trv_output) = self._lwlink.read_trv_status(self._serial)
        if temp is not None:
            self._attr_current_temperature = temp
        if targ is not None:
            if self._inhibit == 0:
                self._target_temperature = targ
                if targ == 0:
                    # TRV off
                    self._target_temperature = None
                if targ >= 40:
                    # Call for heat mode, or TRV in a fixed position
                    self._target_temperature = None
            else:
                # Done the job - use proxy next iteration
                self._inhibit = 0
        if trv_output is not None:
            if trv_output > 0:
                self._attr_hvac_action = CURRENT_HVAC_HEAT
            else:
                self._attr_hvac_action = CURRENT_HVAC_OFF

    @property
    def target_temperature(self):
        """Target room temperature."""
        if self._inhibit > 0:
            # If we get an update before the new temp has
            # propagated, the target temp is set back to the
            # old target on the next poll, showing a false
            # reading temporarily.
            self._target_temperature = self._inhibit
        return self._target_temperature

    def set_temperature(self, **kwargs):
        """Set TRV target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
            self._inhibit = self._target_temperature
        self._lwlink.set_temperature(
            self._device_id, self._target_temperature, self.name
        )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC Mode for TRV."""
