"""The kraken integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KrakenData
from .const import (
    CONF_TRACKED_ASSET_PAIRS,
    DISPATCH_CONFIG_UPDATED,
    DOMAIN,
    SENSOR_TYPES,
    SensorType,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add kraken entities from a config_entry."""

    @callback
    def async_update_sensors(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        dev_reg = device_registry.async_get(hass)

        existing_devices = {
            device.name: device.id
            for device in device_registry.async_entries_for_config_entry(
                dev_reg, config_entry.entry_id
            )
        }

        sensors = []
        for tracked_asset_pair in config_entry.options[CONF_TRACKED_ASSET_PAIRS]:
            # Only create new devices
            if (
                device_name := create_device_name(tracked_asset_pair)
            ) in existing_devices:
                existing_devices.pop(device_name)
            else:
                for sensor_type in SENSOR_TYPES:
                    sensors.append(
                        KrakenSensor(
                            hass.data[DOMAIN],
                            tracked_asset_pair,
                            sensor_type,
                        )
                    )
        async_add_entities(sensors, True)

        # Remove devices for asset pairs which are no longer tracked
        for device_id in existing_devices.values():
            dev_reg.async_remove_device(device_id)

    async_update_sensors(hass, config_entry)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            DISPATCH_CONFIG_UPDATED,
            async_update_sensors,
        )
    )


class KrakenSensor(CoordinatorEntity, SensorEntity):
    """Define a Kraken sensor."""

    def __init__(
        self,
        kraken_data: KrakenData,
        tracked_asset_pair: str,
        sensor_type: SensorType,
    ) -> None:
        """Initialize."""
        assert kraken_data.coordinator is not None
        super().__init__(kraken_data.coordinator)
        self.tracked_asset_pair_wsname = kraken_data.tradable_asset_pairs[
            tracked_asset_pair
        ]
        source_asset = tracked_asset_pair.split("/")[0]
        target_asset = tracked_asset_pair.split("/")[1]
        self._sensor_type = sensor_type["name"]
        self._attr_enabled_by_default = sensor_type["enabled_by_default"]
        if "number_of" not in sensor_type["name"]:
            self._attr_unit_of_measurement = target_asset
        self._device_name = f"{source_asset} {target_asset}"
        self._attr_name = "_".join(
            [
                tracked_asset_pair.split("/")[0],
                tracked_asset_pair.split("/")[1],
                sensor_type["name"],
            ]
        )
        self._attr_icon = "mdi:cash"
        if target_asset == "EUR":
            self._attr_icon = "mdi:currency-eur"
        elif target_asset == "GBP":
            self._attr_icon = "mdi:currency-gbp"
        elif target_asset == "USD":
            self._attr_icon = "mdi:currency-usd"
        elif target_asset == "JPY":
            self._attr_icon = "mdi:currency-jpy"
        elif target_asset == "XBT":
            self._attr_icon = "mdi:currency-btc"
        self._attr_unique_id = self.name.lower()  # type: ignore
        self._received_data_at_least_once = False
        self._available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{source_asset}_{target_asset}")},
            "name": self._device_name,
            "manufacturer": "Kraken.com",
            "entry_type": "service",
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self._update_internal_state()

    def _handle_coordinator_update(self) -> None:
        self._update_internal_state()
        super()._handle_coordinator_update()

    def _update_internal_state(self) -> None:
        try:
            if self._sensor_type == "last_trade_closed":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["last_trade_closed"][0]
            if self._sensor_type == "ask":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["ask"][0]
            if self._sensor_type == "ask_volume":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["ask"][1]
            if self._sensor_type == "bid":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["bid"][0]
            if self._sensor_type == "bid_volume":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["bid"][1]
            if self._sensor_type == "volume_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["volume"][0]
            if self._sensor_type == "volume_last_24h":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["volume"][1]
            if self._sensor_type == "volume_weighted_average_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["volume_weighted_average"][0]
            if self._sensor_type == "volume_weighted_average_last_24h":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["volume_weighted_average"][1]
            if self._sensor_type == "number_of_trades_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["number_of_trades"][0]
            if self._sensor_type == "number_of_trades_last_24h":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["number_of_trades"][1]
            if self._sensor_type == "low_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["low"][0]
            if self._sensor_type == "low_last_24h":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["low"][1]
            if self._sensor_type == "high_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["high"][0]
            if self._sensor_type == "high_last_24h":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["high"][1]
            if self._sensor_type == "opening_price_today":
                self._attr_state = self.coordinator.data[
                    self.tracked_asset_pair_wsname
                ]["opening_price"]
            self._received_data_at_least_once = True  # Received data at least one time.
        except TypeError:
            if self._received_data_at_least_once:
                if self._available:
                    _LOGGER.warning(
                        "Asset Pair %s is no longer available",
                        self._device_name,
                    )
                    self._available = False

    @property
    def available(self) -> bool:
        """Could the api be accessed during the last update call."""
        return self._available and self.coordinator.last_update_success


def create_device_name(tracked_asset_pair: str) -> str:
    """Create the device name for a given tracked asset pair."""
    return f"{tracked_asset_pair.split('/')[0]} {tracked_asset_pair.split('/')[1]}"
