"""Support for interfacing to iTunes API."""
import requests
import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SSL,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
)
import homeassistant.helpers.config_validation as cv

DEFAULT_NAME = "iTunes"
DEFAULT_PORT = 8181
DEFAULT_SSL = False
DEFAULT_TIMEOUT = 10
DOMAIN = "itunes"

SUPPORT_ITUNES = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_SEEK
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PLAY
    | SUPPORT_TURN_OFF
    | SUPPORT_SHUFFLE_SET
)

SUPPORT_AIRPLAY = SUPPORT_VOLUME_SET | SUPPORT_TURN_ON | SUPPORT_TURN_OFF

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
    }
)


class Itunes:
    """The iTunes API client."""

    def __init__(self, host, port, use_ssl):
        """Initialize the iTunes device."""
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

    @property
    def _base_url(self):
        """Return the base URL for endpoints."""
        if self.use_ssl:
            uri_scheme = "https://"
        else:
            uri_scheme = "http://"

        if self.port:
            return f"{uri_scheme}{self.host}:{self.port}"

        return f"{uri_scheme}{self.host}"

    def _request(self, method, path, params=None):
        """Make the actual request and return the parsed response."""
        url = f"{self._base_url}{path}"

        try:
            if method == "GET":
                response = requests.get(url, timeout=DEFAULT_TIMEOUT)
            elif method == "POST":
                response = requests.put(url, params, timeout=DEFAULT_TIMEOUT)
            elif method == "PUT":
                response = requests.put(url, params, timeout=DEFAULT_TIMEOUT)
            elif method == "DELETE":
                response = requests.delete(url, timeout=DEFAULT_TIMEOUT)

            return response.json()
        except requests.exceptions.HTTPError:
            return {"player_state": "error"}
        except requests.exceptions.RequestException:
            return {"player_state": "offline"}

    def _command(self, named_command):
        """Make a request for a controlling command."""
        return self._request("PUT", f"/{named_command}")

    def now_playing(self):
        """Return the current state."""
        return self._request("GET", "/now_playing")

    def set_volume(self, level):
        """Set the volume and returns the current state, level 0-100."""
        return self._request("PUT", "/volume", {"level": level})

    def set_muted(self, muted):
        """Mute and returns the current state, muted True or False."""
        return self._request("PUT", "/mute", {"muted": muted})

    def set_shuffle(self, shuffle):
        """Set the shuffle mode, shuffle True or False."""
        return self._request(
            "PUT", "/shuffle", {"mode": ("songs" if shuffle else "off")}
        )

    def play(self):
        """Set playback to play and returns the current state."""
        return self._command("play")

    def pause(self):
        """Set playback to paused and returns the current state."""
        return self._command("pause")

    def next(self):
        """Skip to the next track and returns the current state."""
        return self._command("next")

    def previous(self):
        """Skip back and returns the current state."""
        return self._command("previous")

    def stop(self):
        """Stop playback and return the current state."""
        return self._command("stop")

    def play_playlist(self, playlist_id_or_name):
        """Set a playlist to be current and returns the current state."""
        response = self._request("GET", "/playlists")
        playlists = response.get("playlists", [])

        found_playlists = [
            playlist
            for playlist in playlists
            if (playlist_id_or_name in [playlist["name"], playlist["id"]])
        ]

        if found_playlists:
            playlist = found_playlists[0]
            path = f"/playlists/{playlist['id']}/play"
            return self._request("PUT", path)

    def artwork_url(self):
        """Return a URL of the current track's album art."""
        return f"{self._base_url}/artwork"

    def airplay_devices(self):
        """Return a list of AirPlay devices."""
        return self._request("GET", "/airplay_devices")

    def airplay_device(self, device_id):
        """Return an AirPlay device."""
        return self._request("GET", f"/airplay_devices/{device_id}")

    def toggle_airplay_device(self, device_id, toggle):
        """Toggle airplay device on or off, id, toggle True or False."""
        command = "on" if toggle else "off"
        path = f"/airplay_devices/{device_id}/{command}"
        return self._request("PUT", path)

    def set_volume_airplay_device(self, device_id, level):
        """Set volume, returns current state of device, id,level 0-100."""
        path = f"/airplay_devices/{device_id}/volume"
        return self._request("PUT", path, {"level": level})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the iTunes platform."""
    add_entities(
        [
            ItunesDevice(
                config.get(CONF_NAME),
                config.get(CONF_HOST),
                config.get(CONF_PORT),
                config[CONF_SSL],
                add_entities,
            )
        ]
    )


class ItunesDevice(MediaPlayerEntity):
    """Representation of an iTunes API instance."""

    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_supported_features = SUPPORT_ITUNES

    def __init__(self, name, host, port, use_ssl, add_entities):
        """Initialize the iTunes device."""
        self._attr_name = name
        self._add_entities = add_entities

        self.client = Itunes(host, port, use_ssl)

        self.airplay_devices = {}

        self.update()

    def update_state(self, state_hash):
        """Update all the state properties with the passed in dictionary."""
        player_state = state_hash.get("player_state", None)
        if player_state == "offline" or player_state is None:
            self._attr_state = "offline"
        elif player_state == "error":
            self._attr_state = "error"
        elif player_state == "stopped":
            self._attr_state = STATE_IDLE
        elif player_state == "paused":
            self._attr_state = STATE_PAUSED
        else:
            self._attr_state = STATE_PLAYING

        self._attr_volume_level = state_hash.get("volume", 0) / 100.0
        self._attr_is_volume_muted = state_hash.get("muted", None)
        self._attr_media_title = state_hash.get("name", None)
        self._attr_media_album_name = state_hash.get("album", None)
        self._attr_media_artist = state_hash.get("artist", None)
        self._attr_media_playlist = state_hash.get("playlist", None)
        self._attr_media_content_id = state_hash.get("id", None)

        _shuffle = state_hash.get("shuffle", None)
        self._attr_shuffle = _shuffle == "songs"
        if (
            player_state in (STATE_PLAYING, STATE_IDLE, STATE_PAUSED)
            and self.media_title is not None
        ):
            self._attr_media_image_url = (
                f"{self.client.artwork_url()}?id={self.media_content_id}"
            )
        else:
            self._attr_media_image_url = (
                "https://cloud.githubusercontent.com/assets/260/9829355"
                "/33fab972-58cf-11e5-8ea2-2ca74bdaae40.png"
            )

    def update(self):
        """Retrieve latest state."""
        now_playing = self.client.now_playing()
        self.update_state(now_playing)

        found_devices = self.client.airplay_devices()
        found_devices = found_devices.get("airplay_devices", [])

        new_devices = []

        for device_data in found_devices:
            device_id = device_data.get("id")

            if self.airplay_devices.get(device_id):
                # update it
                airplay_device = self.airplay_devices.get(device_id)
                airplay_device.update_state(device_data)
            else:
                # add it
                airplay_device = AirPlayDevice(device_id, self.client)
                airplay_device.update_state(device_data)
                self.airplay_devices[device_id] = airplay_device
                new_devices.append(airplay_device)

        if new_devices:
            self._add_entities(new_devices)

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        response = self.client.set_volume(int(volume * 100))
        self.update_state(response)

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        response = self.client.set_muted(mute)
        self.update_state(response)

    def set_shuffle(self, shuffle):
        """Shuffle (true) or no shuffle (false) media player."""
        response = self.client.set_shuffle(shuffle)
        self.update_state(response)

    def media_play(self):
        """Send media_play command to media player."""
        response = self.client.play()
        self.update_state(response)

    def media_pause(self):
        """Send media_pause command to media player."""
        response = self.client.pause()
        self.update_state(response)

    def media_next_track(self):
        """Send media_next command to media player."""
        response = self.client.next()  # pylint: disable=not-callable
        self.update_state(response)

    def media_previous_track(self):
        """Send media_previous command media player."""
        response = self.client.previous()
        self.update_state(response)

    def play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        if media_type == MEDIA_TYPE_PLAYLIST:
            response = self.client.play_playlist(media_id)
            self.update_state(response)

    def turn_off(self):
        """Turn the media player off."""
        response = self.client.stop()
        self.update_state(response)


class AirPlayDevice(MediaPlayerEntity):
    """Representation an AirPlay device via an iTunes API instance."""

    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_supported_features = SUPPORT_AIRPLAY

    def __init__(self, device_id, client):
        """Initialize the AirPlay device."""
        self._id = device_id
        self.client = client
        self._attr_name = "AirPlay"
        self._attr_icon = "mdi:volume-off"
        self._attr_volume_level = 0

    def update_state(self, state_hash):
        """Update all the state properties with the passed in dictionary."""
        if "name" in state_hash:
            self._attr_name = f"{state_hash.get('name', '')} AirTunes Speaker".strip()

        if "selected" in state_hash:
            selected = state_hash.get("selected", None)

        self._attr_state = STATE_ON if selected is True else STATE_OFF
        self._attr_icon = "mdi:volume-high" if selected is True else "mdi:volume-off"

        if "sound_volume" in state_hash:
            self._attr_volume_level = float(state_hash.get("sound_volume", 0)) / 100.0

    def update(self):
        """Retrieve latest state."""

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        volume = int(volume * 100)
        response = self.client.set_volume_airplay_device(self._id, volume)
        self.update_state(response)

    def turn_on(self):
        """Select AirPlay."""
        self.update_state({"selected": True})
        self.schedule_update_ha_state()
        response = self.client.toggle_airplay_device(self._id, True)
        self.update_state(response)

    def turn_off(self):
        """Deselect AirPlay."""
        self.update_state({"selected": False})
        self.schedule_update_ha_state()
        response = self.client.toggle_airplay_device(self._id, False)
        self.update_state(response)
