"""Support for WaterHeater devices of (EMEA/EU) Honeywell TCC systems."""
from __future__ import annotations

import logging

from homeassistant.components.water_heater import (
    SUPPORT_AWAY_MODE,
    SUPPORT_OPERATION_MODE,
    WaterHeaterEntity,
)
from homeassistant.const import PRECISION_TENTHS, PRECISION_WHOLE, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

from . import EvoChild
from .const import DOMAIN, EVO_FOLLOW, EVO_PERMOVER

_LOGGER = logging.getLogger(__name__)

STATE_AUTO = "auto"

HA_STATE_TO_EVO = {STATE_AUTO: "", STATE_ON: "On", STATE_OFF: "Off"}
EVO_STATE_TO_HA = {v: k for k, v in HA_STATE_TO_EVO.items() if k != ""}

STATE_ATTRS_DHW = ["dhwId", "activeFaults", "stateStatus", "temperatureStatus"]


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
) -> None:
    """Create a DHW controller."""
    if discovery_info is None:
        return

    broker = hass.data[DOMAIN]["broker"]

    _LOGGER.debug(
        "Adding: DhwController (%s), id=%s",
        broker.tcs.hotwater.zone_type,
        broker.tcs.hotwater.zoneId,
    )
    new_entity = EvoDHW(broker, broker.tcs.hotwater)

    async_add_entities([new_entity], update_before_add=True)


class EvoDHW(EvoChild, WaterHeaterEntity):
    """Base for a Honeywell TCC DHW controller (aka boiler)."""

    _attr_icon = "mdi:thermometer-lines"
    _attr_name = "DHW controller"
    _attr_operation_list = list(HA_STATE_TO_EVO)

    def __init__(self, evo_broker, evo_device) -> None:
        """Initialize an evohome DHW controller."""
        super().__init__(evo_broker, evo_device)

        self._attr_unique_id = evo_device.dhwId

        self._attr_precision = (
            PRECISION_TENTHS if evo_broker.client_v1 else PRECISION_WHOLE
        )
        self._attr_supported_features = SUPPORT_AWAY_MODE | SUPPORT_OPERATION_MODE

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode for a DHW controller.

        Except for Auto, the mode is only until the next SetPoint.
        """
        if operation_mode == STATE_AUTO:
            await self._evo_broker.call_client_api(self._evo_device.set_dhw_auto())
        else:
            await self._update_schedule()
            until = dt_util.parse_datetime(self.setpoints.get("next_sp_from", ""))
            until = dt_util.as_utc(until) if until else None

            if operation_mode == STATE_ON:
                await self._evo_broker.call_client_api(
                    self._evo_device.set_dhw_on(until=until)
                )
            else:  # STATE_OFF
                await self._evo_broker.call_client_api(
                    self._evo_device.set_dhw_off(until=until)
                )

    async def async_turn_away_mode_on(self):
        """Turn away mode on."""
        await self._evo_broker.call_client_api(self._evo_device.set_dhw_off())

    async def async_turn_away_mode_off(self):
        """Turn away mode off."""
        await self._evo_broker.call_client_api(self._evo_device.set_dhw_auto())

    async def async_turn_on(self):
        """Turn on."""
        await self._evo_broker.call_client_api(self._evo_device.set_dhw_on())

    async def async_turn_off(self):
        """Turn off."""
        await self._evo_broker.call_client_api(self._evo_device.set_dhw_off())

    async def async_update(self) -> None:
        """Get the latest state data for a DHW controller."""
        await super().async_update()

        for attr in STATE_ATTRS_DHW:
            self._device_state_attrs[attr] = getattr(self._evo_device, attr)
        self._attr_state = EVO_STATE_TO_HA[self._evo_device.stateStatus["state"]]
        self._attr_current_operation = STATE_AUTO
        if self._evo_device.stateStatus["mode"] != EVO_FOLLOW:
            self._attr_current_operation = EVO_STATE_TO_HA[
                self._evo_device.stateStatus["state"]
            ]
        is_off = EVO_STATE_TO_HA[self._evo_device.stateStatus["state"]] == STATE_OFF
        is_permanent = self._evo_device.stateStatus["mode"] == EVO_PERMOVER
        self._attr_is_away_mode_on = is_off and is_permanent
