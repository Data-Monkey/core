"""Sensor for Last.fm account status."""
import hashlib
import logging
import re

import pylast as lastfm
from pylast import WSError
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION, CONF_API_KEY
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_LAST_PLAYED = "last_played"
ATTR_PLAY_COUNT = "play_count"
ATTR_TOP_PLAYED = "top_played"
ATTRIBUTION = "Data provided by Last.fm"

STATE_NOT_SCROBBLING = "Not Scrobbling"

CONF_USERS = "users"

ICON = "mdi:radio-fm"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_USERS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Last.fm sensor platform."""
    api_key = config[CONF_API_KEY]
    users = config.get(CONF_USERS)

    lastfm_api = lastfm.LastFMNetwork(api_key=api_key)

    entities = []
    for username in users:
        try:
            lastfm_api.get_user(username).get_image()
            entities.append(LastfmSensor(username, lastfm_api))
        except WSError as error:
            _LOGGER.error(error)
            return

    add_entities(entities, True)


class LastfmSensor(SensorEntity):
    """A class for the Last.fm account."""

    _attr_icon = ICON

    def __init__(self, user, lastfm_api):
        """Initialize the sensor."""
        self._attr_unique_id = hashlib.sha256(user.encode("utf-8")).hexdigest()
        self._user = lastfm_api.get_user(user)
        self._attr_name = user
        self._attr_state = STATE_NOT_SCROBBLING
        self._attr_extra_state_attributes = {}
        self._attr_extra_state_attributes[ATTR_ATTRIBUTION] = ATTRIBUTION

    def update(self):
        """Update device state."""
        self._attr_entity_picture = self._user.get_image()
        self._attr_extra_state_attributes[ATTR_PLAY_COUNT] = self._user.get_playcount()

        recent_tracks = self._user.get_recent_tracks(limit=2)
        if recent_tracks:
            last = recent_tracks[0]
            lastplayed = f"{last.track.artist} - {last.track.title}"
            self._attr_extra_state_attributes[ATTR_LAST_PLAYED] = lastplayed

        top_tracks = self._user.get_top_tracks(limit=1)
        if top_tracks:
            top = top_tracks[0]
            toptitle = re.search("', '(.+?)',", str(top))
            topartist = re.search("'(.+?)',", str(top))
            topplayed = f"{topartist.group(1)} - {toptitle.group(1)}"
            self._attr_extra_state_attributes[ATTR_TOP_PLAYED] = topplayed

        now_playing = self._user.get_now_playing()
        if now_playing is None:
            self._attr_state = STATE_NOT_SCROBBLING
        else:
            self._attr_state = f"{now_playing.artist} - {now_playing.title}"
