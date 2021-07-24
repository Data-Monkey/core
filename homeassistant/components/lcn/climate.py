"""Support for LCN climate control."""
from __future__ import annotations

from typing import Any, cast

import pypck

from homeassistant.components.climate import (
    DOMAIN as DOMAIN_CLIMATE,
    ClimateEntity,
    const,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_ADDRESS,
    CONF_DOMAIN,
    CONF_ENTITIES,
    CONF_SOURCE,
    CONF_UNIT_OF_MEASUREMENT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import LcnEntity
from .const import (
    CONF_DOMAIN_DATA,
    CONF_LOCKABLE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SETPOINT,
)
from .helpers import DeviceConnectionType, InputType, get_device_connection

PARALLEL_UPDATES = 0


def create_lcn_climate_entity(
    hass: HomeAssistantType, entity_config: ConfigType, config_entry: ConfigEntry
) -> LcnEntity:
    """Set up an entity for this domain."""
    device_connection = get_device_connection(
        hass, entity_config[CONF_ADDRESS], config_entry
    )

    return LcnClimate(entity_config, config_entry.entry_id, device_connection)


async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LCN switch entities from a config entry."""
    entities = []

    for entity_config in config_entry.data[CONF_ENTITIES]:
        if entity_config[CONF_DOMAIN] == DOMAIN_CLIMATE:
            entities.append(
                create_lcn_climate_entity(hass, entity_config, config_entry)
            )

    async_add_entities(entities)


class LcnClimate(LcnEntity, ClimateEntity):
    """Representation of a LCN climate device."""

    _attr_supported_features = const.SUPPORT_TARGET_TEMPERATURE

    def __init__(
        self, config: ConfigType, entry_id: str, device_connection: DeviceConnectionType
    ) -> None:
        """Initialize of a LCN climate device."""
        super().__init__(config, entry_id, device_connection)

        self.variable = pypck.lcn_defs.Var[config[CONF_DOMAIN_DATA][CONF_SOURCE]]
        self.setpoint = pypck.lcn_defs.Var[config[CONF_DOMAIN_DATA][CONF_SETPOINT]]
        self.unit = pypck.lcn_defs.VarUnit.parse(
            config[CONF_DOMAIN_DATA][CONF_UNIT_OF_MEASUREMENT]
        )

        self.regulator_id = pypck.lcn_defs.Var.to_set_point_id(self.setpoint)
        self._attr_max_temp = cast(float, config[CONF_DOMAIN_DATA][CONF_MAX_TEMP])
        self._attr_min_temp = cast(float, config[CONF_DOMAIN_DATA][CONF_MIN_TEMP])

        self._is_on = True
        self._attr_temperature_unit = TEMP_CELSIUS
        if self.unit == pypck.lcn_defs.VarUnit.FAHRENHEIT:
            self._attr_temperature_unit = TEMP_FAHRENHEIT
        modes = [const.HVAC_MODE_HEAT]
        if config[CONF_DOMAIN_DATA][CONF_LOCKABLE]:
            modes.append(const.HVAC_MODE_OFF)
        self._attr_hvac_modes = modes

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if not self.device_connection.is_group:
            await self.device_connection.activate_status_request_handler(self.variable)
            await self.device_connection.activate_status_request_handler(self.setpoint)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if not self.device_connection.is_group:
            await self.device_connection.cancel_status_request_handler(self.variable)
            await self.device_connection.cancel_status_request_handler(self.setpoint)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == const.HVAC_MODE_HEAT:
            if not await self.device_connection.lock_regulator(
                self.regulator_id, False
            ):
                return
            self._is_on = True
            self._attr_hvac_mode = const.HVAC_MODE_HEAT
            self.async_write_ha_state()
        elif hvac_mode == const.HVAC_MODE_OFF:
            if not await self.device_connection.lock_regulator(self.regulator_id, True):
                return
            self._is_on = False
            self._attr_hvac_mode = const.HVAC_MODE_OFF
            self._attr_target_temperature = None
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if not await self.device_connection.var_abs(
            self.setpoint, temperature, self.unit
        ):
            return
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    def input_received(self, input_obj: InputType) -> None:
        """Set temperature value when LCN input object is received."""
        if not isinstance(input_obj, pypck.inputs.ModStatusVar):
            return

        if input_obj.get_var() == self.variable:
            self._attr_current_temperature = input_obj.get_value().to_var_unit(
                self.unit
            )
        elif input_obj.get_var() == self.setpoint:
            self._is_on = not input_obj.get_value().is_locked_regulator()
            if self._is_on:
                self._attr_target_temperature = input_obj.get_value().to_var_unit(
                    self.unit
                )
                self._attr_hvac_mode = const.HVAC_MODE_HEAT
            else:
                self._attr_hvac_mode = const.HVAC_MODE_OFF

        self.async_write_ha_state()
