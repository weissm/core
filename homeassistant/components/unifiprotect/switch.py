"""Component providing Switches for UniFi Protect."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import Any

from uiprotect.data import (
    NVR,
    Camera,
    ModelType,
    ProtectAdoptableDeviceModel,
    ProtectModelWithId,
    RecordingMode,
    VideoMode,
)

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .data import ProtectData, UFPConfigEntry
from .entity import (
    BaseProtectEntity,
    ProtectDeviceEntity,
    ProtectNVREntity,
    async_all_device_entities,
)
from .models import PermRequired, ProtectRequiredKeysMixin, ProtectSetableKeysMixin, T

_LOGGER = logging.getLogger(__name__)
ATTR_PREV_MIC = "prev_mic_level"
ATTR_PREV_RECORD = "prev_record_mode"


@dataclass(frozen=True, kw_only=True)
class ProtectSwitchEntityDescription(
    ProtectSetableKeysMixin[T], SwitchEntityDescription
):
    """Describes UniFi Protect Switch entity."""


async def _set_highfps(obj: Camera, value: bool) -> None:
    if value:
        await obj.set_video_mode(VideoMode.HIGH_FPS)
    else:
        await obj.set_video_mode(VideoMode.DEFAULT)


CAMERA_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="ssh",
        name="SSH Enabled",
        icon="mdi:lock",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        ufp_value="is_ssh_enabled",
        ufp_set_method="set_ssh",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="status_light",
        name="Status Light On",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="feature_flags.has_led_status",
        ufp_value="led_settings.is_enabled",
        ufp_set_method="set_status_light",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="hdr_mode",
        name="HDR Mode",
        icon="mdi:brightness-7",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        ufp_required_field="feature_flags.has_hdr",
        ufp_value="hdr_mode",
        ufp_set_method="set_hdr",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription[Camera](
        key="high_fps",
        name="High FPS",
        icon="mdi:video-high-definition",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="feature_flags.has_highfps",
        ufp_value="is_high_fps_enabled",
        ufp_set_method_fn=_set_highfps,
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="system_sounds",
        name="System Sounds",
        icon="mdi:speaker",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="has_speaker",
        ufp_value="speaker_settings.are_system_sounds_enabled",
        ufp_enabled="feature_flags.has_speaker",
        ufp_set_method="set_system_sounds",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="osd_name",
        name="Overlay: Show Name",
        icon="mdi:fullscreen",
        entity_category=EntityCategory.CONFIG,
        ufp_value="osd_settings.is_name_enabled",
        ufp_set_method="set_osd_name",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="osd_date",
        name="Overlay: Show Date",
        icon="mdi:fullscreen",
        entity_category=EntityCategory.CONFIG,
        ufp_value="osd_settings.is_date_enabled",
        ufp_set_method="set_osd_date",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="osd_logo",
        name="Overlay: Show Logo",
        icon="mdi:fullscreen",
        entity_category=EntityCategory.CONFIG,
        ufp_value="osd_settings.is_logo_enabled",
        ufp_set_method="set_osd_logo",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="osd_bitrate",
        name="Overlay: Show Nerd Mode",
        icon="mdi:fullscreen",
        entity_category=EntityCategory.CONFIG,
        ufp_value="osd_settings.is_debug_enabled",
        ufp_set_method="set_osd_bitrate",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="color_night_vision",
        name="Color Night Vision",
        icon="mdi:light-flood-down",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="has_color_night_vision",
        ufp_value="isp_settings.is_color_night_vision_enabled",
        ufp_set_method="set_color_night_vision",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="motion",
        name="Detections: Motion",
        icon="mdi:run-fast",
        entity_category=EntityCategory.CONFIG,
        ufp_value="recording_settings.enable_motion_detection",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_motion_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_person",
        name="Detections: Person",
        icon="mdi:walk",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_person",
        ufp_value="is_person_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_person_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_vehicle",
        name="Detections: Vehicle",
        icon="mdi:car",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_vehicle",
        ufp_value="is_vehicle_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_vehicle_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_animal",
        name="Detections: Animal",
        icon="mdi:paw",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_animal",
        ufp_value="is_animal_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_animal_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_package",
        name="Detections: Package",
        icon="mdi:package-variant-closed",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_package",
        ufp_value="is_package_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_package_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_licenseplate",
        name="Detections: License Plate",
        icon="mdi:car",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_license_plate",
        ufp_value="is_license_plate_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_license_plate_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_smoke",
        name="Detections: Smoke",
        icon="mdi:fire",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_smoke",
        ufp_value="is_smoke_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_smoke_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_cmonx",
        name="Detections: CO",
        icon="mdi:molecule-co",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_co",
        ufp_value="is_co_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_cmonx_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_siren",
        name="Detections: Siren",
        icon="mdi:alarm-bell",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_siren",
        ufp_value="is_siren_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_siren_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_baby_cry",
        name="Detections: Baby Cry",
        icon="mdi:cradle",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_baby_cry",
        ufp_value="is_baby_cry_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_baby_cry_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_speak",
        name="Detections: Speaking",
        icon="mdi:account-voice",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_speaking",
        ufp_value="is_speaking_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_speaking_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_bark",
        name="Detections: Barking",
        icon="mdi:dog",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_bark",
        ufp_value="is_bark_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_bark_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_car_alarm",
        name="Detections: Car Alarm",
        icon="mdi:car",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_car_alarm",
        ufp_value="is_car_alarm_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_car_alarm_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_car_horn",
        name="Detections: Car Horn",
        icon="mdi:bugle",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_car_horn",
        ufp_value="is_car_horn_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_car_horn_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="smart_glass_break",
        name="Detections: Glass Break",
        icon="mdi:glass-fragile",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="can_detect_glass_break",
        ufp_value="is_glass_break_detection_on",
        ufp_enabled="is_recording_enabled",
        ufp_set_method="set_glass_break_detection",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="track_person",
        name="Tracking: Person",
        icon="mdi:walk",
        entity_category=EntityCategory.CONFIG,
        ufp_required_field="is_ptz",
        ufp_value="is_person_tracking_enabled",
        ufp_set_method="set_person_track",
        ufp_perm=PermRequired.WRITE,
    ),
)

PRIVACY_MODE_SWITCH = ProtectSwitchEntityDescription[Camera](
    key="privacy_mode",
    name="Privacy Mode",
    icon="mdi:eye-settings",
    entity_category=EntityCategory.CONFIG,
    ufp_required_field="feature_flags.has_privacy_mask",
    ufp_value="is_privacy_on",
    ufp_perm=PermRequired.WRITE,
)

SENSE_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="status_light",
        name="Status Light On",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
        ufp_value="led_settings.is_enabled",
        ufp_set_method="set_status_light",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="motion",
        name="Motion Detection",
        icon="mdi:walk",
        entity_category=EntityCategory.CONFIG,
        ufp_value="motion_settings.is_enabled",
        ufp_set_method="set_motion_status",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="temperature",
        name="Temperature Sensor",
        icon="mdi:thermometer",
        entity_category=EntityCategory.CONFIG,
        ufp_value="temperature_settings.is_enabled",
        ufp_set_method="set_temperature_status",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="humidity",
        name="Humidity Sensor",
        icon="mdi:water-percent",
        entity_category=EntityCategory.CONFIG,
        ufp_value="humidity_settings.is_enabled",
        ufp_set_method="set_humidity_status",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="light",
        name="Light Sensor",
        icon="mdi:brightness-5",
        entity_category=EntityCategory.CONFIG,
        ufp_value="light_settings.is_enabled",
        ufp_set_method="set_light_status",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="alarm",
        name="Alarm Sound Detection",
        entity_category=EntityCategory.CONFIG,
        ufp_value="alarm_settings.is_enabled",
        ufp_set_method="set_alarm_status",
        ufp_perm=PermRequired.WRITE,
    ),
)


LIGHT_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="ssh",
        name="SSH Enabled",
        icon="mdi:lock",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        ufp_value="is_ssh_enabled",
        ufp_set_method="set_ssh",
        ufp_perm=PermRequired.WRITE,
    ),
    ProtectSwitchEntityDescription(
        key="status_light",
        name="Status Light On",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
        ufp_value="light_device_settings.is_indicator_enabled",
        ufp_set_method="set_status_light",
        ufp_perm=PermRequired.WRITE,
    ),
)

DOORLOCK_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="status_light",
        name="Status Light On",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
        ufp_value="led_settings.is_enabled",
        ufp_set_method="set_status_light",
        ufp_perm=PermRequired.WRITE,
    ),
)

VIEWER_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="ssh",
        name="SSH Enabled",
        icon="mdi:lock",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        ufp_value="is_ssh_enabled",
        ufp_set_method="set_ssh",
        ufp_perm=PermRequired.WRITE,
    ),
)

NVR_SWITCHES: tuple[ProtectSwitchEntityDescription, ...] = (
    ProtectSwitchEntityDescription(
        key="analytics_enabled",
        name="Analytics Enabled",
        icon="mdi:google-analytics",
        entity_category=EntityCategory.CONFIG,
        ufp_value="is_analytics_enabled",
        ufp_set_method="set_anonymous_analytics",
    ),
    ProtectSwitchEntityDescription(
        key="insights_enabled",
        name="Insights Enabled",
        icon="mdi:magnify",
        entity_category=EntityCategory.CONFIG,
        ufp_value="is_insights_enabled",
        ufp_set_method="set_insights",
    ),
)

_MODEL_DESCRIPTIONS: dict[ModelType, Sequence[ProtectRequiredKeysMixin]] = {
    ModelType.CAMERA: CAMERA_SWITCHES,
    ModelType.LIGHT: LIGHT_SWITCHES,
    ModelType.SENSOR: SENSE_SWITCHES,
    ModelType.DOORLOCK: DOORLOCK_SWITCHES,
    ModelType.VIEWPORT: VIEWER_SWITCHES,
}

_PRIVACY_MODEL_DESCRIPTIONS: dict[ModelType, Sequence[ProtectRequiredKeysMixin]] = {
    ModelType.CAMERA: [PRIVACY_MODE_SWITCH]
}


class ProtectSwitch(ProtectDeviceEntity, SwitchEntity):
    """A UniFi Protect Switch."""

    entity_description: ProtectSwitchEntityDescription
    _state_attrs = ("_attr_available", "_attr_is_on")

    def __init__(
        self,
        data: ProtectData,
        device: ProtectAdoptableDeviceModel,
        description: ProtectSwitchEntityDescription,
    ) -> None:
        """Initialize an UniFi Protect Switch."""
        super().__init__(data, device, description)
        self._attr_name = f"{self.device.display_name} {self.entity_description.name}"
        self._switch_type = self.entity_description.key

    def _async_update_device_from_protect(self, device: ProtectModelWithId) -> None:
        super()._async_update_device_from_protect(device)
        self._attr_is_on = self.entity_description.get_ufp_value(self.device) is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self.entity_description.ufp_set(self.device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self.entity_description.ufp_set(self.device, False)


class ProtectNVRSwitch(ProtectNVREntity, SwitchEntity):
    """A UniFi Protect NVR Switch."""

    entity_description: ProtectSwitchEntityDescription
    _state_attrs = ("_attr_available", "_attr_is_on")

    def __init__(
        self,
        data: ProtectData,
        device: NVR,
        description: ProtectSwitchEntityDescription,
    ) -> None:
        """Initialize an UniFi Protect Switch."""
        super().__init__(data, device, description)
        self._attr_name = f"{self.device.display_name} {self.entity_description.name}"

    def _async_update_device_from_protect(self, device: ProtectModelWithId) -> None:
        super()._async_update_device_from_protect(device)
        self._attr_is_on = self.entity_description.get_ufp_value(self.device) is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self.entity_description.ufp_set(self.device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self.entity_description.ufp_set(self.device, False)


class ProtectPrivacyModeSwitch(RestoreEntity, ProtectSwitch):
    """A UniFi Protect Switch."""

    device: Camera

    def __init__(
        self,
        data: ProtectData,
        device: ProtectAdoptableDeviceModel,
        description: ProtectSwitchEntityDescription,
    ) -> None:
        """Initialize an UniFi Protect Switch."""
        super().__init__(data, device, description)

        if self.device.is_privacy_on:
            extra_state = self.extra_state_attributes or {}
            self._previous_mic_level = extra_state.get(ATTR_PREV_MIC, 100)
            self._previous_record_mode = extra_state.get(
                ATTR_PREV_RECORD, RecordingMode.ALWAYS
            )
        else:
            self._previous_mic_level = self.device.mic_volume
            self._previous_record_mode = self.device.recording_settings.mode

    @callback
    def _update_previous_attr(self) -> None:
        if self.is_on:
            self._attr_extra_state_attributes = {
                ATTR_PREV_MIC: self._previous_mic_level,
                ATTR_PREV_RECORD: self._previous_record_mode,
            }
        else:
            self._attr_extra_state_attributes = {}

    @callback
    def _async_update_device_from_protect(self, device: ProtectModelWithId) -> None:
        super()._async_update_device_from_protect(device)
        # do not add extra state attribute on initialize
        if self.entity_id:
            self._update_previous_attr()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        self._previous_mic_level = self.device.mic_volume
        self._previous_record_mode = self.device.recording_settings.mode
        await self.device.set_privacy(True, 0, RecordingMode.NEVER)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        extra_state = self.extra_state_attributes or {}
        prev_mic = extra_state.get(ATTR_PREV_MIC, self._previous_mic_level)
        prev_record = extra_state.get(ATTR_PREV_RECORD, self._previous_record_mode)
        await self.device.set_privacy(False, prev_mic, prev_record)

    async def async_added_to_hass(self) -> None:
        """Restore extra state attributes on startp up."""
        await super().async_added_to_hass()
        if not (last_state := await self.async_get_last_state()):
            return
        last_attrs = last_state.attributes
        self._previous_mic_level = last_attrs.get(
            ATTR_PREV_MIC, self._previous_mic_level
        )
        self._previous_record_mode = last_attrs.get(
            ATTR_PREV_RECORD, self._previous_record_mode
        )
        self._update_previous_attr()


MODEL_DESCRIPTIONS_WITH_CLASS = (
    (_MODEL_DESCRIPTIONS, ProtectSwitch),
    (_PRIVACY_MODEL_DESCRIPTIONS, ProtectPrivacyModeSwitch),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UFPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for UniFi Protect integration."""
    data = entry.runtime_data

    @callback
    def _add_new_device(device: ProtectAdoptableDeviceModel) -> None:
        entities: list[BaseProtectEntity] = []
        for model_descriptions, klass in MODEL_DESCRIPTIONS_WITH_CLASS:
            entities += async_all_device_entities(
                data, klass, model_descriptions=model_descriptions, ufp_device=device
            )
        async_add_entities(entities)

    data.async_subscribe_adopt(_add_new_device)
    entities: list[BaseProtectEntity] = []
    for model_descriptions, klass in MODEL_DESCRIPTIONS_WITH_CLASS:
        entities += async_all_device_entities(
            data, klass, model_descriptions=model_descriptions
        )

    bootstrap = data.api.bootstrap
    nvr = bootstrap.nvr
    if nvr.can_write(bootstrap.auth_user) and nvr.is_insights_enabled is not None:
        entities.extend(
            ProtectNVRSwitch(data, device=nvr, description=switch)
            for switch in NVR_SWITCHES
        )
    async_add_entities(entities)
