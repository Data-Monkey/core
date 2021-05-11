"""Test Goal Zero Yeti config flow."""
from unittest.mock import patch

from goalzero import exceptions

from homeassistant.components.dhcp import HOSTNAME, IP_ADDRESS, MAC_ADDRESS
from homeassistant.components.goalzero.const import DEFAULT_NAME, DOMAIN
from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)
from homeassistant.setup import async_setup_component

from . import CONF_DATA, _create_mocked_yeti, _patch_config_flow_yeti


def _flow_next(hass, flow_id):
    return next(
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["flow_id"] == flow_id
    )


def _patch_setup():
    return patch(
        "homeassistant.components.goalzero.async_setup_entry",
        return_value=True,
    )


async def test_flow_user(hass):
    """Test user initialized flow."""
    mocked_yeti = await _create_mocked_yeti()
    with _patch_config_flow_yeti(mocked_yeti), _patch_setup():
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

    with _patch_config_flow_yeti(mocked_yeti), _patch_setup():
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_DATA,
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"


async def test_flow_user_cannot_connect(hass):
    """Test user initialized flow with unreachable server."""
    mocked_yeti = await _create_mocked_yeti(True)
    with _patch_config_flow_yeti(mocked_yeti) as yetimock:
        yetimock.side_effect = exceptions.ConnectError
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_invalid_host(hass):
    """Test user initialized flow with invalid server."""
    mocked_yeti = await _create_mocked_yeti(True)
    with _patch_config_flow_yeti(mocked_yeti) as yetimock:
        yetimock.side_effect = exceptions.InvalidHost
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "invalid_host"}


async def test_flow_user_unknown_error(hass):
    """Test user initialized flow with unreachable server."""
    mocked_yeti = await _create_mocked_yeti(True)
    with _patch_config_flow_yeti(mocked_yeti) as yetimock:
        yetimock.side_effect = Exception
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}


async def test_dhcp_discovery(hass):
    """Test we can process the discovery from dhcp."""
    await async_setup_component(hass, "persistent_notification", {})
    mocked_yeti = await _create_mocked_yeti()
    with _patch_config_flow_yeti(mocked_yeti), _patch_setup():
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_DHCP},
            data={
                IP_ADDRESS: "1.1.1.1",
                MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
                HOSTNAME: "any",
            },
        )
        assert result["type"] == "form"
        assert result["errors"] == {}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await hass.async_block_till_done()

        assert result["type"] == RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == {
            CONF_HOST: "1.1.1.1",
            CONF_NAME: "Yeti",
        }

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_DHCP},
            data={
                IP_ADDRESS: "1.1.1.1",
                MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
                HOSTNAME: "any",
            },
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"
