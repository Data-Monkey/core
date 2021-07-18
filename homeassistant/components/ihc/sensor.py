"""Support for IHC sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, DEVICE_CLASS_TEMPERATURE
from homeassistant.util.unit_system import TEMPERATURE_UNITS

from . import IHC_CONTROLLER, IHC_INFO
from .ihcdevice import IHCDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the IHC sensor platform."""
    if discovery_info is None:
        return
    devices = []
    for name, device in discovery_info.items():
        ihc_id = device["ihc_id"]
        product_cfg = device["product_cfg"]
        product = device["product"]
        # Find controller that corresponds with device id
        ctrl_id = device["ctrl_id"]
        ihc_key = f"ihc{ctrl_id}"
        info = hass.data[ihc_key][IHC_INFO]
        ihc_controller = hass.data[ihc_key][IHC_CONTROLLER]
        unit = product_cfg[CONF_UNIT_OF_MEASUREMENT]
        sensor = IHCSensor(ihc_controller, name, ihc_id, info, unit, product)
        devices.append(sensor)
    add_entities(devices)


class IHCSensor(IHCDevice, SensorEntity):
    """Implementation of the IHC sensor."""

    def __init__(
        self, ihc_controller, name, ihc_id: int, info: bool, unit, product=None
    ) -> None:
        """Initialize the IHC sensor."""
        super().__init__(ihc_controller, name, ihc_id, info, product)
        self._attr_unit_of_measurement = unit
        if unit in TEMPERATURE_UNITS:
            self._attr_device_class = DEVICE_CLASS_TEMPERATURE

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        self._attr_state = value
        self.schedule_update_ha_state()
