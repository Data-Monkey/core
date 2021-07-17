"""Interfaces with iAlarm control panels."""
import logging

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
)
from homeassistant.core import T
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up a iAlarm alarm control panel based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([IAlarmPanel(coordinator)], False)


class IAlarmPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Representation of an iAlarm device."""

    _attr_name = "iAlarm"
    _attr_supported_features = SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY

    def __init__(self, coordinator: DataUpdateCoordinator[T]) -> None:
        """Initialize an iAlarm device."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.mac  # type: ignore
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(self.unique_id))},
            "name": str(self.name),
            "manufacturer": "Antifurto365 - Meian",
        }

    @property
    def state(self):
        """Return the state of the device."""
        return self.coordinator.state

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self.coordinator.ialarm.disarm()

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self.coordinator.ialarm.arm_stay()

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self.coordinator.ialarm.arm_away()
