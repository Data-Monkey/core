"""Support for Logi Circle sensors."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_BATTERY_CHARGING,
    CONF_MONITORED_CONDITIONS,
    CONF_SENSORS,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.util.dt import as_local

from .const import (
    ATTRIBUTION,
    DEVICE_BRAND,
    DOMAIN as LOGI_CIRCLE_DOMAIN,
    LOGI_SENSORS as SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a sensor for a Logi Circle device. Obsolete."""
    _LOGGER.warning("Logi Circle no longer works with sensor platform configuration")


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Logi Circle sensor based on a config entry."""
    devices = await hass.data[LOGI_CIRCLE_DOMAIN].cameras

    sensors = []
    for sensor_type in entry.data.get(CONF_SENSORS).get(CONF_MONITORED_CONDITIONS):
        for device in devices:
            if device.supports_feature(sensor_type):
                sensors.append(LogiSensor(device, sensor_type))

    async_add_entities(sensors, True)


class LogiSensor(SensorEntity):
    """A sensor implementation for a Logi Circle camera."""

    def __init__(self, camera, sensor_type):
        """Initialize a sensor for Logi Circle camera."""
        self._sensor_type = sensor_type
        self._camera = camera
        self._attr_unique_id = f"{camera.mac_address}-{sensor_type}"
        self._attr_icon = f"mdi:{SENSOR_TYPES.get(sensor_type)[2]}"
        self._attr_name = f"{camera.name} {SENSOR_TYPES.get(sensor_type)[0]}"
        self._attr_unit_of_measurement = SENSOR_TYPES.get(sensor_type)[1]

    async def async_update(self):
        """Get the latest data and updates the state."""
        _LOGGER.debug("Pulling data from %s sensor", self.name)
        await self._camera.update()

        if self._sensor_type == "last_activity_time":
            last_activity = await self._camera.get_last_activity(force_refresh=True)
            if last_activity is not None:
                last_activity_time = as_local(last_activity.end_time_utc)
                self._attr_state = (
                    f"{last_activity_time.hour:0>2}:{last_activity_time.minute:0>2}"
                )
        else:
            state = getattr(self._camera, self._sensor_type, None)
            self._attr_state = state

        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "battery_saving_mode": (
                STATE_ON if self._camera.battery_saving else STATE_OFF
            ),
            "microphone_gain": self._camera.microphone_gain,
        }
        if self._sensor_type == "battery_level":
            self._attr_extra_state_attributes[
                ATTR_BATTERY_CHARGING
            ] = self._camera.charging

        if self._sensor_type == "battery_level" and self.state is not None:
            self._attr_icon = icon_for_battery_level(
                battery_level=int(self.state), charging=False
            )
        elif self._sensor_type == "recording_mode" and self.state is not None:
            self._attr_icon = "mdi:eye" if self.state == STATE_ON else "mdi:eye-off"
        elif self._sensor_type == "streaming_mode" and self.state is not None:
            self._attr_icon = (
                "mdi:camera" if self.state == STATE_ON else "mdi:camera-off"
            )
        else:
            self._attr_icon = f"mdi:{SENSOR_TYPES.get(self._sensor_type)[2]}"

        self._attr_device_info = {
            "name": self._camera.name,
            "identifiers": {(LOGI_CIRCLE_DOMAIN, self._camera.id)},
            "model": self._camera.model_name,
            "sw_version": self._camera.firmware,
            "manufacturer": DEVICE_BRAND,
        }
