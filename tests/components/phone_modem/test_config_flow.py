"""Test Phone Modem config flow."""
from unittest.mock import patch

import phone_modem

from homeassistant.components.phone_modem.const import (
    DEFAULT_DEVICE,
    DEFAULT_NAME,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from . import CONF_DATA, _create_mocked_modem, _patch_config_flow_modem

from tests.common import MockConfigEntry


def _flow_next(hass, flow_id):
    return next(
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["flow_id"] == flow_id
    )


def _patch_setup():
    return patch(
        "homeassistant.components.phone_modem.async_setup_entry",
        return_value=True,
    )


async def test_flow_user(hass):
    """Test user initialized flow."""
    mocked_modem = await _create_mocked_modem()
    with _patch_config_flow_modem(mocked_modem), _patch_setup():
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_DATA,
        )
        assert result["type"] == RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == DEFAULT_NAME
        assert result["data"] == CONF_DATA


async def test_flow_user_already_configured(hass):
    """Test user initialized flow with duplicate device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_NAME: DEFAULT_NAME, CONF_PORT: DEFAULT_DEVICE},
    )

    entry.add_to_hass(hass)

    service_info = {
        "name": DEFAULT_NAME,
        "port": DEFAULT_DEVICE,
    }
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=service_info
    )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_flow_user_unknown_error(hass):
    """Test user initialized flow with unreachable device."""
    mocked_modem = await _create_mocked_modem(True)
    with _patch_config_flow_modem(mocked_modem) as modemmock:
        modemmock.side_effect = phone_modem.exceptions.SerialError
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}
