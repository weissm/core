"""Support for Big Ass Fans binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from aiobafi6 import Device

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BAFConfigEntry
from .entity import BAFEntity


@dataclass(frozen=True, kw_only=True)
class BAFBinarySensorDescription(
    BinarySensorEntityDescription,
):
    """Class describing BAF binary sensor entities."""

    value_fn: Callable[[Device], bool | None]


OCCUPANCY_SENSORS = (
    BAFBinarySensorDescription(
        key="occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda device: cast(bool | None, device.fan_occupancy_detected),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BAFConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BAF binary sensors."""
    device = entry.runtime_data
    sensors_descriptions: list[BAFBinarySensorDescription] = []
    if device.has_occupancy:
        sensors_descriptions.extend(OCCUPANCY_SENSORS)
    async_add_entities(
        BAFBinarySensor(device, description) for description in sensors_descriptions
    )


class BAFBinarySensor(BAFEntity, BinarySensorEntity):
    """BAF binary sensor."""

    entity_description: BAFBinarySensorDescription

    def __init__(self, device: Device, description: BAFBinarySensorDescription) -> None:
        """Initialize the entity."""
        self.entity_description = description
        super().__init__(device)
        self._attr_unique_id = f"{self._device.mac_address}-{description.key}"

    @callback
    def _async_update_attrs(self) -> None:
        """Update attrs from device."""
        description = self.entity_description
        self._attr_is_on = description.value_fn(self._device)
