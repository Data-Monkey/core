"""Adapter to wrap the pyjuicenet api for home assistant."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class JuiceNetDevice(CoordinatorEntity):
    """Represent a base JuiceNet device."""

    def __init__(self, device, sensor_type, coordinator):
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.device = device
        self.type = sensor_type
        self._attr_name = device.name
        self._attr_unique_id = f"{device.id}-{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.id)},
            "name": device.name,
            "manufacturer": "JuiceNet",
        }
