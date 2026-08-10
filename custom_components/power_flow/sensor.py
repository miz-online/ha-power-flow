from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from homeassistant.components.sensor import SensorDeviceClass
except ImportError:
    from homeassistant.const import DEVICE_CLASS_POWER as SensorDeviceClass

try:
    from homeassistant.const import POWER_WATT
except ImportError:
    POWER_WATT = "W"

from .const import DATA_COORDINATOR, DOMAIN, DEFAULT_TARGET
from .data import PowerFlowCoordinator


def _sensor_device_info(coordinator) -> DeviceInfo:
    # Hub device info uses the config entry id so a hub Device is created
    # for each ConfigEntry. `coordinator` is a PowerFlowCoordinator and
    # provides the entry id.
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.entry.entry_id)},
        name="Power Flow",
        manufacturer="Custom",
        model="Power Flow Integration",
    )


class PowerFlowGroupSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: PowerFlowCoordinator, group_name: str, is_leftover: bool = False) -> None:
        super().__init__(coordinator)
        self.group_name = group_name
        self.is_leftover = is_leftover

    @property
    def name(self) -> str:
        if self.is_leftover:
            return self.coordinator.leftover_name
        return f"{self.group_name} Power"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        # Provide a quick link to the integration options for this config entry
        return {"configure_url": f"/config/integrations/config_entry/{self.coordinator.entry.entry_id}/options"}

    @property
    def unique_id(self) -> str:
        if self.is_leftover:
            return f"{self.coordinator.entry.entry_id}_leftover"
        return f"{self.coordinator.entry.entry_id}_group_{self.group_name}"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data["groups"].get(self.group_name, 0.0)

    @property
    def native_unit_of_measurement(self) -> str:
        return POWER_WATT

    @property
    def device_class(self) -> SensorDeviceClass:
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> str:
        return SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        # Attach group sensors to the hub device for this config entry
        return _sensor_device_info(self.coordinator)


class PowerFlowConnectionSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: PowerFlowCoordinator, source: str, target: str) -> None:
        super().__init__(coordinator)
        self.source = source
        self.target = target

    @property
    def name(self) -> str:
        return f"{self.source} → {self.target} Flow"

    @property
    def unique_id(self) -> str:
        safe_source = self.source.replace(" ", "_")
        safe_target = self.target.replace(" ", "_")
        return f"{self.coordinator.entry.entry_id}_flow_{safe_source}_{safe_target}"

    @property
    def native_value(self) -> float | None:
        connection_key = f"{self.source}|{self.target}"
        return self.coordinator.data["connections"].get(connection_key, {}).get("value", 0.0)

    @property
    def native_unit_of_measurement(self) -> str:
        return POWER_WATT

    @property
    def device_class(self) -> SensorDeviceClass:
        return SensorDeviceClass.POWER

    @property
    def state_class(self) -> str:
        return SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
        }
        

    @property
    def device_info(self) -> DeviceInfo:
        # Create a per-logical-device DeviceInfo for the source device and link
        # it to the hub via `via_device` using the config entry id.
        safe_source = self.source.strip().lower().replace(" ", "_")
        hub_identifier = (DOMAIN, self.coordinator.entry.entry_id)
        device_identifier = (DOMAIN, f"{self.coordinator.entry.entry_id}_device_{safe_source}")
        return DeviceInfo(
            identifiers={device_identifier},
            name=self.source,
            via_device=hub_identifier,
            manufacturer="Custom",
            model="Power Flow Device",
        )


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: PowerFlowCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    data = coordinator.data
    for group_name in sorted(data["groups"].keys()):
        if group_name == DEFAULT_TARGET:
            entities.append(PowerFlowGroupSensor(coordinator, group_name, is_leftover=True))
        else:
            entities.append(PowerFlowGroupSensor(coordinator, group_name))

    for connection_data in data["connections"].values():
        entities.append(
            PowerFlowConnectionSensor(
                coordinator,
                connection_data["source"],
                connection_data["target"],
            )
        )

    async_add_entities(entities, update_before_add=True)
