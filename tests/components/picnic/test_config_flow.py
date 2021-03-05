"""Test the Picnic config flow."""
from unittest.mock import patch

import requests

from homeassistant import config_entries, setup
from homeassistant.components.picnic.config_flow import InvalidAuth
from homeassistant.components.picnic.const import DOMAIN


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] is None

    auth_data = {
        "user_id": "f29-2a6-o32n",
        "address": {
            "street": "Teststreet",
            "house_number": 123,
            "house_number_ext": "b",
        },
    }
    with patch(
        "homeassistant.components.picnic.config_flow.PicnicHub.authenticate",
        return_value=auth_data,
    ), patch(
        "homeassistant.components.picnic.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.picnic.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Teststreet 123b"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
        "country_code": "NL",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=requests.exceptions.ConnectionError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
