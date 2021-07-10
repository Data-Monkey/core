"""The DoorBird integration base entity."""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .const import (
    DOORBIRD_INFO_KEY_BUILD_NUMBER,
    DOORBIRD_INFO_KEY_DEVICE_TYPE,
    DOORBIRD_INFO_KEY_FIRMWARE,
    MANUFACTURER,
)
from .util import get_mac_address_from_doorstation_info


class DoorBirdEntity(Entity):
    """Base class for doorbird entities."""

    def __init__(self, doorstation, doorstation_info):
        """Initialize the entity."""
        super().__init__()
        self._attr_device_info = {
            "connections": {
                (
                    dr.CONNECTION_NETWORK_MAC,
                    get_mac_address_from_doorstation_info(doorstation_info),
                )
            },
            "name": doorstation.name,
            "manufacturer": MANUFACTURER,
            "sw_version": f"{doorstation_info[DOORBIRD_INFO_KEY_FIRMWARE]} {doorstation_info[DOORBIRD_INFO_KEY_BUILD_NUMBER]}",
            "model": doorstation_info[DOORBIRD_INFO_KEY_DEVICE_TYPE],
        }
