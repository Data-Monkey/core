"""Sensor for checking the status of London Underground tube lines."""
from datetime import timedelta

from london_tube_status import TubeData
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION
import homeassistant.helpers.config_validation as cv

ATTRIBUTION = "Powered by TfL Open Data"

CONF_LINE = "line"

ICON = "mdi:subway"

SCAN_INTERVAL = timedelta(seconds=30)

TUBE_LINES = [
    "Bakerloo",
    "Central",
    "Circle",
    "District",
    "DLR",
    "Hammersmith & City",
    "Jubilee",
    "London Overground",
    "Metropolitan",
    "Northern",
    "Piccadilly",
    "TfL Rail",
    "Victoria",
    "Waterloo & City",
]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_LINE): vol.All(cv.ensure_list, [vol.In(list(TUBE_LINES))])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tube sensor."""

    data = TubeData()
    data.update()
    sensors = []
    for line in config.get(CONF_LINE):
        sensors.append(LondonTubeSensor(line, data))

    add_entities(sensors, True)


class LondonTubeSensor(SensorEntity):
    """Sensor that reads the status of a line from Tube Data."""

    _attr_icon = ICON

    def __init__(self, name, data):
        """Initialize the London Underground sensor."""
        self._data = data
        self._attr_name = name
        self._attr_extra_state_attributes = {ATTR_ATTRIBUTION: ATTRIBUTION}

    def update(self):
        """Update the sensor."""
        self._data.update()
        self._attr_state = self._data.data[self.name]["State"]
        self._attr_extra_state_attributes["Description"] = self._data.data[self.name][
            "Description"
        ]
