"""Support for Lutron Powr Savr occupancy sensors."""
from pylutron import OccupancyGroup

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_OCCUPANCY,
    BinarySensorEntity,
)

from . import LUTRON_DEVICES, LutronDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron occupancy sensors."""
    if discovery_info is None:
        return
    devs = []
    for (area_name, device) in hass.data[LUTRON_DEVICES]["binary_sensor"]:
        dev = LutronOccupancySensor(area_name, device)
        devs.append(dev)

    add_entities(devs)


class LutronOccupancySensor(LutronDevice, BinarySensorEntity):
    """Representation of a Lutron Occupancy Group.

    The Lutron integration API reports "occupancy groups" rather than
    individual sensors. If two sensors are in the same room, they're
    reported as a single occupancy group.
    """

    _attr_device_class = DEVICE_CLASS_OCCUPANCY

    def __init__(self, area_name, lutron_device):
        """Initialize a Lutron Occupancy Group."""
        super().__init__(area_name, lutron_device)
        self._attr_name = f"{self._area_name} Occupancy"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        # Error cases will end up treated as unoccupied.
        return self._lutron_device.state == OccupancyGroup.State.OCCUPIED

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"lutron_integration_id": self._lutron_device.id}
