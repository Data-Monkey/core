"""Support for monitoring the state of Linode Nodes."""
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOVING,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
import homeassistant.helpers.config_validation as cv

from . import (
    ATTR_CREATED,
    ATTR_IPV4_ADDRESS,
    ATTR_IPV6_ADDRESS,
    ATTR_MEMORY,
    ATTR_NODE_ID,
    ATTR_NODE_NAME,
    ATTR_REGION,
    ATTR_VCPUS,
    CONF_NODES,
    DATA_LINODE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Node"
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_NODES): vol.All(cv.ensure_list, [cv.string])}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Linode droplet sensor."""
    linode = hass.data.get(DATA_LINODE)
    nodes = config.get(CONF_NODES)

    dev = []
    for node in nodes:
        node_id = linode.get_node_id(node)
        if node_id is None:
            _LOGGER.error("Node %s is not available", node)
            return
        dev.append(LinodeBinarySensor(linode, node_id))

    add_entities(dev, True)


class LinodeBinarySensor(BinarySensorEntity):
    """Representation of a Linode droplet sensor."""

    _attr_device_class = DEVICE_CLASS_MOVING

    def __init__(self, li, node_id):
        """Initialize a new Linode sensor."""
        self._linode = li
        self._node_id = node_id
        self.data = None
        self._attr_extra_state_attributes = {}

    def update(self):
        """Update state of sensor."""
        self._linode.update()
        if self._linode.data is not None:
            for node in self._linode.data:
                if node.id == self._node_id:
                    self.data = node
        if self.data is not None:
            self._attr_is_on = self.data.status == "running"
            self._attr_extra_state_attributes = {
                ATTR_CREATED: self.data.created,
                ATTR_NODE_ID: self.data.id,
                ATTR_NODE_NAME: self.data.label,
                ATTR_IPV4_ADDRESS: self.data.ipv4,
                ATTR_IPV6_ADDRESS: self.data.ipv6,
                ATTR_MEMORY: self.data.specs.memory,
                ATTR_REGION: self.data.region.country,
                ATTR_VCPUS: self.data.specs.vcpus,
            }
            self._attr_name = self.data.label
