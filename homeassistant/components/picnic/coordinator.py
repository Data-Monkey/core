"""Coordinator to fetch data from the Picnic API."""
import copy
from datetime import timedelta
import logging

import async_timeout
from python_picnic_api import PicnicAPI

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ADDRESS,
    SENSOR_CART_ITEMS_COUNT,
    SENSOR_CART_TOTAL_PRICE,
    SENSOR_COMPLETED_DELIVERIES,
    SENSOR_LAST_ORDER_DELIVERY_TIME,
    SENSOR_LAST_ORDER_ETA_END,
    SENSOR_LAST_ORDER_ETA_START,
    SENSOR_LAST_ORDER_SLOT_END,
    SENSOR_LAST_ORDER_SLOT_START,
    SENSOR_LAST_ORDER_STATUS,
    SENSOR_LAST_ORDER_TOTAL_PRICE,
    SENSOR_SELECTED_SLOT_END,
    SENSOR_SELECTED_SLOT_MAX_ODER_TIME,
    SENSOR_SELECTED_SLOT_MIN_ORDER_VALUE,
    SENSOR_SELECTED_SLOT_START,
    SENSOR_TOTAL_ORDERS,
)


class PicnicUpdateCoordinator(DataUpdateCoordinator):
    """The coordinator to fetch data from the Picnic API at a set interval."""

    def __init__(self, hass: HomeAssistant, picnic_api_client: PicnicAPI):
        """Initialize the coordinator with the given Picnic API client."""
        self.picnic_api_client = picnic_api_client

        logger = logging.getLogger(__name__)
        super().__init__(
            hass,
            logger,
            name="Picnic coordinator",
            update_interval=timedelta(minutes=30),
            update_method=self.async_update_data,
        )

    async def async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await self.hass.async_add_executor_job(self.fetch_data)
        except Exception as err:  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with API: {err}")

    def fetch_data(self):
        """Fetch the data from the Picnic API and return a flat dict with only needed sensor data."""
        # Fetch from the API and pre-process the data
        user = self.picnic_api_client.get_user()
        cart = self.picnic_api_client.get_cart()
        last_order = self._get_last_order()

        if not user or not cart or not last_order:
            raise UpdateFailed("API response doesn't contain expected data.")

        slot_data = self._get_slot_data(cart)
        address = f'{user["address"]["street"]} {user["address"]["house_number"]}{user["address"]["house_number_ext"]}'
        minimum_order_value = (
            slot_data["minimum_order_value"] / 100
            if slot_data.get("minimum_order_value")
            else None
        )
        # Create a flat lookup table to be used in the entities, convert prices from cents to euros
        return {
            ADDRESS: address,
            SENSOR_COMPLETED_DELIVERIES: user.get("completed_deliveries", 0),
            SENSOR_TOTAL_ORDERS: user.get("total_deliveries"),
            SENSOR_CART_ITEMS_COUNT: cart.get("total_count", 0),
            SENSOR_CART_TOTAL_PRICE: cart.get("total_price", 0) / 100,
            SENSOR_SELECTED_SLOT_START: slot_data.get("window_start"),
            SENSOR_SELECTED_SLOT_END: slot_data.get("window_end"),
            SENSOR_SELECTED_SLOT_MAX_ODER_TIME: slot_data.get("cut_off_time"),
            SENSOR_SELECTED_SLOT_MIN_ORDER_VALUE: minimum_order_value,
            SENSOR_LAST_ORDER_SLOT_START: last_order["slot"].get("window_start"),
            SENSOR_LAST_ORDER_SLOT_END: last_order["slot"].get("window_end"),
            SENSOR_LAST_ORDER_STATUS: last_order.get("status"),
            SENSOR_LAST_ORDER_ETA_START: last_order["eta"].get("start"),
            SENSOR_LAST_ORDER_ETA_END: last_order["eta"].get("end"),
            SENSOR_LAST_ORDER_DELIVERY_TIME: last_order["delivery_time"].get("start"),
            SENSOR_LAST_ORDER_TOTAL_PRICE: last_order.get("total_price", 0) / 100,
        }

    @staticmethod
    def _get_slot_data(cart: dict) -> dict:
        """Get the selected slot, if it's explicitly selected."""
        selected_slot = cart.get("selected_slot", {})
        available_slots = cart.get("delivery_slots", [])

        if selected_slot.get("state") == "EXPLICIT":
            slot_data = filter(
                lambda slot: slot.get("slot_id") == selected_slot.get("slot_id"),
                available_slots,
            )
            if slot_data:
                return next(slot_data)

        return {}

    def _get_last_order(self) -> dict:
        """Get data of the last order from the list of deliveries."""
        # Get the deliveries
        deliveries = self.picnic_api_client.get_deliveries(summary=True)
        if not len(deliveries):
            return {}

        # Determine the last order and get the position details
        last_order = deliveries[0]
        delivery_position = self.picnic_api_client.get_delivery_position(
            last_order["delivery_id"]
        )

        # Determine the ETA, if available, the one from the delivery position API is more precise
        # but it's only available shortly before the actual delivery.
        last_order["eta"] = delivery_position.get(
            "eta_window", last_order.get("eta2", {})
        )

        # Determine the total price by adding up the total price of all sub-orders
        total_price = 0
        for order in last_order.get("orders", []):
            total_price += order.get("total_price", 0)

        # Sanitise the object
        last_order["total_price"] = total_price
        last_order.setdefault("delivery_time", {})
        if "eta2" in last_order:
            del last_order["eta2"]

        # Make a copy because some references are local
        return copy.deepcopy(last_order)
