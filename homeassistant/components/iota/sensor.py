"""Support for IOTA wallet sensors."""
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME

from . import CONF_WALLETS, IotaDevice

ATTR_TESTNET = "testnet"
ATTR_URL = "url"

CONF_IRI = "iri"
CONF_SEED = "seed"
CONF_TESTNET = "testnet"

SCAN_INTERVAL = timedelta(minutes=3)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the IOTA sensor."""
    iota_config = discovery_info
    sensors = [
        IotaBalanceSensor(wallet, iota_config) for wallet in iota_config[CONF_WALLETS]
    ]

    sensors.append(IotaNodeSensor(iota_config=iota_config))

    add_entities(sensors)


class IotaBalanceSensor(IotaDevice, SensorEntity):
    """Implement an IOTA sensor for displaying wallets balance."""

    _attr_unit_of_measurement = "IOTA"

    def __init__(self, wallet_config, iota_config):
        """Initialize the sensor."""
        super().__init__(
            name=wallet_config[CONF_NAME],
            seed=wallet_config[CONF_SEED],
            iri=iota_config[CONF_IRI],
            is_testnet=iota_config[CONF_TESTNET],
        )
        self._attr_name = f"{self.name} Balance"

    def update(self):
        """Fetch new balance from IRI."""
        self._attr_state = self.api.get_inputs()["totalBalance"]


class IotaNodeSensor(IotaDevice, SensorEntity):
    """Implement an IOTA sensor for displaying attributes of node."""

    _attr_name = "IOTA Node"

    def __init__(self, iota_config):
        """Initialize the sensor."""
        super().__init__(
            name="Node Info",
            seed=None,
            iri=iota_config[CONF_IRI],
            is_testnet=iota_config[CONF_TESTNET],
        )
        self._attr_extra_state_attributes = {
            ATTR_URL: self.iri,
            ATTR_TESTNET: self.is_testnet,
        }

    def update(self):
        """Fetch new attributes IRI node."""
        node_info = self.api.get_node_info()
        self._attr_state = node_info.get("appVersion")

        # convert values to raw string formats
        self._attr_extra_state_attributes.update(
            {k: str(v) for k, v in node_info.items()}
        )
