"""Support for magicseaweed data from magicseaweed.com."""
from datetime import timedelta
import logging

import magicseaweed
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

CONF_HOURS = "hours"
CONF_SPOT_ID = "spot_id"
CONF_UNITS = "units"

DEFAULT_UNIT = "us"
DEFAULT_NAME = "MSW"
DEFAULT_ATTRIBUTION = "Data provided by magicseaweed.com"

ICON = "mdi:waves"

HOURS = ["12AM", "3AM", "6AM", "9AM", "12PM", "3PM", "6PM", "9PM"]

SENSOR_TYPES = {
    "max_breaking_swell": ["Max"],
    "min_breaking_swell": ["Min"],
    "swell_forecast": ["Forecast"],
}

UNITS = ["eu", "uk", "us"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MONITORED_CONDITIONS): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_SPOT_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_HOURS, default=None): vol.All(
            cv.ensure_list, [vol.In(HOURS)]
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNITS): vol.In(UNITS),
    }
)

# Return cached results if last scan was less then this time ago.
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Magicseaweed sensor."""
    name = config.get(CONF_NAME)
    spot_id = config[CONF_SPOT_ID]
    api_key = config[CONF_API_KEY]
    hours = config.get(CONF_HOURS)

    if CONF_UNITS in config:
        units = config.get(CONF_UNITS)
    elif hass.config.units.is_metric:
        units = UNITS[0]
    else:
        units = UNITS[2]

    forecast_data = MagicSeaweedData(api_key=api_key, spot_id=spot_id, units=units)
    forecast_data.update()

    # If connection failed don't setup platform.
    if forecast_data.currently is None or forecast_data.hourly is None:
        return

    sensors = []
    for variable in config[CONF_MONITORED_CONDITIONS]:
        sensors.append(MagicSeaweedSensor(forecast_data, variable, name))
        if "forecast" not in variable and hours is not None:
            for hour in hours:
                sensors.append(MagicSeaweedSensor(forecast_data, variable, name, hour))
    add_entities(sensors, True)


class MagicSeaweedSensor(SensorEntity):
    """Implementation of a MagicSeaweed sensor."""

    _attr_icon = ICON

    def __init__(self, forecast_data, sensor_type, name, hour=None):
        """Initialize the sensor."""
        self.client_name = name
        self.data = forecast_data
        self.hour = hour
        self.type = sensor_type
        self._attr_extra_state_attributes = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._attr_name = SENSOR_TYPES[sensor_type][0]

    def update(self):
        """Get the latest data from Magicseaweed and updates the states."""
        self.data.update()
        if self.hour is None:
            forecast = self.data.currently
            if "forecast" in self.type:
                self._attr_name = f"{self.client_name} {self.name}"
            else:
                self._attr_name = f"Current {self.client_name} {self.name}"
        else:
            forecast = self.data.hourly[self.hour]
            self._attr_name = f"{self.hour} {self.client_name} {self.name}"

        self._attr_unit_of_measurement = forecast.swell_unit
        if self.type == "min_breaking_swell":
            self._attr_state = forecast.swell_minBreakingHeight
        elif self.type == "max_breaking_swell":
            self._attr_state = forecast.swell_maxBreakingHeight
        elif self.type == "swell_forecast":
            summary = f"{forecast.swell_minBreakingHeight} - {forecast.swell_maxBreakingHeight}"
            self._attr_state = summary
            if self.hour is None:
                for hour, data in self.data.hourly.items():
                    occurs = hour
                    hr_summary = f"{data.swell_minBreakingHeight} - {data.swell_maxBreakingHeight} {data.swell_unit}"
                    self._attr_extra_state_attributes[occurs] = hr_summary

        if self.type != "swell_forecast":
            self._attr_extra_state_attributes.update(forecast.attrs)


class MagicSeaweedData:
    """Get the latest data from MagicSeaweed."""

    def __init__(self, api_key, spot_id, units):
        """Initialize the data object."""
        self._msw = magicseaweed.MSW_Forecast(api_key, spot_id, None, units)
        self.currently = None
        self.hourly = {}

        # Apply throttling to methods using configured interval
        self.update = Throttle(MIN_TIME_BETWEEN_UPDATES)(self._update)

    def _update(self):
        """Get the latest data from MagicSeaweed."""
        try:
            forecasts = self._msw.get_future()
            self.currently = forecasts.data[0]
            for forecast in forecasts.data[:8]:
                hour = dt_util.utc_from_timestamp(forecast.localTimestamp).strftime(
                    "%-I%p"
                )
                self.hourly[hour] = forecast
        except ConnectionError:
            _LOGGER.error("Unable to retrieve data from Magicseaweed")
