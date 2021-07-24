"""Support for LG soundbars."""
import temescal

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import STATE_ON

SUPPORT_LG = (
    SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_SELECT_SOUND_MODE
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the LG platform."""
    if discovery_info is not None:
        add_entities([LGDevice(discovery_info)])


class LGDevice(MediaPlayerEntity):
    """Representation of an LG soundbar device."""

    _attr_should_poll = False
    _attr_state = STATE_ON
    _attr_supported_features = SUPPORT_LG

    def __init__(self, discovery_info):
        """Initialize the LG speakers."""
        self._host = discovery_info["host"]
        self._port = discovery_info["port"]
        self._attr_name = discovery_info["hostname"].split(".")[0]
        self._volume = 0
        self._volume_max = 0
        self._function = -1
        self._functions = []
        self._equaliser = -1
        self._equalisers = []
        self._attr_is_volume_muted = True
        self._device = None

    async def async_added_to_hass(self):
        """Register the callback after hass is ready for it."""
        await self.hass.async_add_executor_job(self._connect)

    def _connect(self):
        """Perform the actual devices setup."""
        self._device = temescal.temescal(
            self._host, port=self._port, callback=self.handle_event
        )
        self.update()

    def handle_event(self, response):
        """Handle responses from the speakers."""
        data = response["data"]
        if response["msg"] == "EQ_VIEW_INFO":
            if "ai_eq_list" in data:
                self._equalisers = data["ai_eq_list"]
            if "i_curr_eq" in data:
                self._equaliser = data["i_curr_eq"]
        elif response["msg"] == "SPK_LIST_VIEW_INFO":
            if "i_vol" in data:
                self._volume = data["i_vol"]
            if "s_user_name" in data:
                self._attr_name = data["s_user_name"]
            if "i_vol_max" in data:
                self._volume_max = data["i_vol_max"]
            if "b_mute" in data:
                self._attr_is_volume_muted = data["b_mute"]
            if "i_curr_func" in data:
                self._function = data["i_curr_func"]
        elif response["msg"] == "FUNC_VIEW_INFO":
            if "i_curr_func" in data:
                self._function = data["i_curr_func"]
            if "ai_func_list" in data:
                self._functions = data["ai_func_list"]
        elif response["msg"] == "SETTING_VIEW_INFO":
            if "i_curr_eq" in data:
                self._equaliser = data["i_curr_eq"]
            if "s_user_name" in data:
                self._attr_name = data["s_user_name"]
        self.schedule_update_ha_state()

    def update(self):
        """Trigger updates from the device."""
        self._device.get_eq()
        self._device.get_info()
        self._device.get_func()
        self._device.get_settings()
        self._device.get_product_info()

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume_max != 0:
            return self._volume / self._volume_max
        return 0

    @property
    def sound_mode(self):
        """Return the current sound mode."""
        if self._equaliser == -1 or self._equaliser >= len(temescal.equalisers):
            return None
        return temescal.equalisers[self._equaliser]

    @property
    def sound_mode_list(self):
        """Return the available sound modes."""
        modes = []
        for equaliser in self._equalisers:
            if equaliser < len(temescal.equalisers):
                modes.append(temescal.equalisers[equaliser])
        return sorted(modes)

    @property
    def source(self):
        """Return the current input source."""
        if self._function == -1 or self._function >= len(temescal.functions):
            return None
        return temescal.functions[self._function]

    @property
    def source_list(self):
        """List of available input sources."""
        sources = []
        for function in self._functions:
            if function < len(temescal.functions):
                sources.append(temescal.functions[function])
        return sorted(sources)

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        volume = volume * self._volume_max
        self._device.set_volume(int(volume))

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._device.set_mute(mute)

    def select_source(self, source):
        """Select input source."""
        self._device.set_func(temescal.functions.index(source))

    def select_sound_mode(self, sound_mode):
        """Set Sound Mode for Receiver.."""
        self._device.set_eq(temescal.equalisers.index(sound_mode))
