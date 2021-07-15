"""Play media via gstreamer."""
import logging

from gsp import GstreamerPlayer
import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP, STATE_IDLE
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_PIPELINE = "pipeline"

DOMAIN = "gstreamer"

SUPPORT_GSTREAMER = (
    SUPPORT_VOLUME_SET
    | SUPPORT_PLAY
    | SUPPORT_PAUSE
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_NEXT_TRACK
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string, vol.Optional(CONF_PIPELINE): cv.string}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Gstreamer platform."""

    name = config.get(CONF_NAME)
    pipeline = config.get(CONF_PIPELINE)
    player = GstreamerPlayer(pipeline)

    def _shutdown(call):
        """Quit the player on shutdown."""
        player.quit()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown)
    add_entities([GstreamerDevice(player, name)])


class GstreamerDevice(MediaPlayerEntity):
    """Representation of a Gstreamer device."""

    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_supported_features = SUPPORT_GSTREAMER

    def __init__(self, player, name):
        """Initialize the Gstreamer device."""
        self._player = player
        self._attr_name = name or DOMAIN
        self._attr_state = STATE_IDLE

    def update(self):
        """Update properties."""
        self._attr_state = self._player.state
        self._attr_volume_level = self._player.volume
        self._attr_media_duration = self._player.duration
        self._attr_media_content_id = self._player.uri
        self._attr_media_title = self._player.title
        self._attr_media_album_name = self._player.album
        self._attr_media_artist = self._player.artist

    def set_volume_level(self, volume):
        """Set the volume level."""
        self._player.volume = volume

    def play_media(self, media_type, media_id, **kwargs):
        """Play media."""
        if media_type != MEDIA_TYPE_MUSIC:
            _LOGGER.error("Invalid media type")
            return
        self._player.queue(media_id)

    def media_play(self):
        """Play."""
        self._player.play()

    def media_pause(self):
        """Pause."""
        self._player.pause()

    def media_next_track(self):
        """Next track."""
        self._player.next()
