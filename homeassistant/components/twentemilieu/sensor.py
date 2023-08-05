"""Support for Twente Milieu sensors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from twentemilieu import WasteType

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import TwenteMilieuEntity


@dataclass
class TwenteMilieuSensorDescriptionMixin:
    """Define an entity description mixin."""

    waste_type: WasteType


@dataclass
class TwenteMilieuSensorDescription(
    SensorEntityDescription, TwenteMilieuSensorDescriptionMixin
):
    """Describe an Ambient PWS binary sensor."""


SENSORS: tuple[TwenteMilieuSensorDescription, ...] = (
    TwenteMilieuSensorDescription(
        key="tree",
        translation_key="christmas_tree_pickup",
        waste_type=WasteType.TREE,
        icon="mdi:pine-tree",
        device_class=SensorDeviceClass.DATE,
    ),
    TwenteMilieuSensorDescription(
        key="Non-recyclable",
        translation_key="non_recyclable_waste_pickup",
        waste_type=WasteType.NON_RECYCLABLE,
        icon="mdi:delete-empty",
        device_class=SensorDeviceClass.DATE,
    ),
    TwenteMilieuSensorDescription(
        key="Organic",
        translation_key="organic_waste_pickup",
        waste_type=WasteType.ORGANIC,
        icon="mdi:delete-empty",
        device_class=SensorDeviceClass.DATE,
    ),
    TwenteMilieuSensorDescription(
        key="Paper",
        translation_key="paper_waste_pickup",
        waste_type=WasteType.PAPER,
        icon="mdi:delete-empty",
        device_class=SensorDeviceClass.DATE,
    ),
    TwenteMilieuSensorDescription(
        key="Plastic",
        translation_key="packages_waste_pickup",
        waste_type=WasteType.PACKAGES,
        icon="mdi:delete-empty",
        device_class=SensorDeviceClass.DATE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Twente Milieu sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.data[CONF_ID]]
    async_add_entities(
        TwenteMilieuSensor(coordinator, description, entry) for description in SENSORS
    )


class TwenteMilieuSensor(TwenteMilieuEntity, SensorEntity):
    """Defines a Twente Milieu sensor."""

    entity_description: TwenteMilieuSensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[WasteType, list[date]]],
        description: TwenteMilieuSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Twente Milieu entity."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{entry.data[CONF_ID]}_{description.key}"

    @property
    def native_value(self) -> date | None:
        """Return the state of the sensor."""
        if not (dates := self.coordinator.data[self.entity_description.waste_type]):
            return None
        return dates[0]
