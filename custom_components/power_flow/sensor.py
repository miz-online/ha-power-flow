from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import POWER_WATT
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, DEFAULT_TARGET
from .data import PowerFlowCoordinator


def _sensor_device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, DOMAIN)},
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
        return _sensor_device_info()


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
        return _sensor_device_info()


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
