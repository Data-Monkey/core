"""Support for LG TV running on NetCast 3 or 4."""
from datetime import datetime, timedelta

from pylgnetcast import LgNetCastClient, LgNetCastError
from requests import RequestException
import voluptuous as vol

from homeassistant import util
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_NAME,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.script import Script

DEFAULT_NAME = "LG TV Remote"

CONF_ON_ACTION = "turn_on_action"

MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

SUPPORT_LGTV = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_PLAY
    | SUPPORT_PLAY_MEDIA
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ON_ACTION): cv.SCRIPT_SCHEMA,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_ACCESS_TOKEN): vol.All(cv.string, vol.Length(max=6)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the LG TV platform."""

    host = config.get(CONF_HOST)
    access_token = config.get(CONF_ACCESS_TOKEN)
    name = config.get(CONF_NAME)
    on_action = config.get(CONF_ON_ACTION)

    client = LgNetCastClient(host, access_token)
    domain = __name__.split(".")[-2]
    on_action_script = Script(hass, on_action, name, domain) if on_action else None

    add_entities([LgTVDevice(client, name, on_action_script)], True)


class LgTVDevice(MediaPlayerEntity):
    """Representation of a LG TV."""

    _attr_media_content_type = MEDIA_TYPE_CHANNEL

    def __init__(self, client, name, on_action_script):
        """Initialize the LG TV device."""
        self._client = client
        self._attr_name = name
        self._attr_is_volume_muted = False
        self._on_action_script = on_action_script
        # Assume that the TV is in Play mode
        self._playing = True
        self._attr_volume_level = 0
        self._attr_source = ""
        self._attr_media_title = ""
        self._sources = {}
        self._attr_source_list = []
        self._attr_supported_features = SUPPORT_LGTV
        if on_action_script:
            self._attr_supported_features = SUPPORT_LGTV | SUPPORT_TURN_ON

    def send_command(self, command):
        """Send remote control commands to the TV."""

        try:
            with self._client as client:
                client.send_command(command)
        except (LgNetCastError, RequestException):
            self._attr_state = STATE_OFF

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Retrieve the latest data from the LG TV."""

        try:
            with self._client as client:
                self._attr_state = STATE_PLAYING
                volume_info = client.query_data("volume_info")
                if volume_info:
                    volume_info = volume_info[0]
                    self._attr_volume_level = (
                        float(volume_info.find("level").text) / 100.0
                    )
                    self._attr_is_volume_muted = volume_info.find("mute").text == "true"

                channel_info = client.query_data("cur_channel")
                if channel_info:
                    channel_info = channel_info[0]
                    channel_id = channel_info.find("major")
                    self._attr_source = channel_info.find("chname").text
                    self._attr_media_title = channel_info.find("progName").text
                    if channel_id is not None:
                        self._attr_media_content_id = int(channel_id.text)
                    if self.source is None:
                        self._attr_source = channel_info.find("inputSourceName").text
                    if self.media_title is None:
                        self._attr_media_title = channel_info.find("labelName").text

                channel_list = client.query_data("channel_list")
                if channel_list:
                    channel_names = []
                    for channel in channel_list:
                        channel_name = channel.find("chname")
                        if channel_name is not None:
                            channel_names.append(str(channel_name.text))
                    self._sources = dict(zip(channel_names, channel_list))
                    # sort source names by the major channel number
                    source_tuples = [
                        (k, source.find("major").text)
                        for k, source in self._sources.items()
                    ]
                    sorted_sources = sorted(
                        source_tuples, key=lambda channel: int(channel[1])
                    )
                    self._attr_source_list = [n for n, k in sorted_sources]
        except (LgNetCastError, RequestException):
            self._attr_state = STATE_OFF

    @property
    def media_image_url(self):
        """URL for obtaining a screen capture."""
        return (
            f"{self._client.url}data?target=screen_image&_={datetime.now().timestamp()}"
        )

    def turn_off(self):
        """Turn off media player."""
        self.send_command(1)

    def turn_on(self):
        """Turn on the media player."""
        if self._on_action_script:
            self._on_action_script.run(context=self._context)

    def volume_up(self):
        """Volume up the media player."""
        self.send_command(24)

    def volume_down(self):
        """Volume down media player."""
        self.send_command(25)

    def mute_volume(self, mute):
        """Send mute command."""
        self.send_command(26)

    def select_source(self, source):
        """Select input source."""
        self._client.change_channel(self._sources[source])

    def media_play_pause(self):
        """Simulate play pause media player."""
        if self._playing:
            self.media_pause()
        else:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self._playing = True
        self._attr_state = STATE_PLAYING
        self.send_command(33)

    def media_pause(self):
        """Send media pause command to media player."""
        self._playing = False
        self._attr_state = STATE_PAUSED
        self.send_command(34)

    def media_next_track(self):
        """Send next track command."""
        self.send_command(36)

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_command(37)

    def play_media(self, media_type, media_id, **kwargs):
        """Tune to channel."""
        if media_type != MEDIA_TYPE_CHANNEL:
            raise ValueError(f"Invalid media type: {media_type}")

        for name, channel in self._sources.items():
            channel_id = channel.find("major")
            if channel_id is not None and int(channel_id.text) == int(media_id):
                self.select_source(name)
                return

        raise ValueError(f"Invalid media id: {media_id}")
