from __future__ import annotations

import logging

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICES,
    CONF_INVERT_POWER_SENSOR,
    CONF_LEFTOVER_NAME,
    CONF_MQTT_EXPOSE_CONNECTIONS,
    CONF_MQTT_ROOT,
    CONF_NAME,
    CONF_POWER_EXPORT_SENSOR,
    CONF_POWER_IMPORT_SENSOR,
    CONF_POWER_SENSOR,
    CONF_TARGET,
    DEFAULT_LEFTOVER_NAME,
    DEFAULT_MQTT_EXPOSE_CONNECTIONS,
    DEFAULT_TARGET,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class FlowDefinition:
    name: str
    target: str
    power_sensor: str | None = None
    invert_power_sensor: bool = False
    power_import_sensor: str | None = None
    power_export_sensor: str | None = None


class PowerFlowCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Power Flow Coordinator",
            update_interval=None,
        )
        self.entry = entry
        self._unsub = None
        self._flows = self._normalize_flows(entry.data.get(CONF_DEVICES, []))
        self.leftover_name = entry.data.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME)
        self.mqtt_root = entry.data.get(CONF_MQTT_ROOT, "")
        self.mqtt_expose_connections = entry.data.get(
            CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
        )

    async def async_initialize(self) -> None:
        self._setup_listeners()
        await self.async_refresh()

    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _setup_listeners(self) -> None:
        entity_ids = {
            sensor
            for flow in self._flows
            for sensor in (
                flow.power_sensor,
                flow.power_import_sensor,
                flow.power_export_sensor,
            )
            if sensor
        }
        if self._unsub is not None:
            self._unsub()

        if entity_ids:
            self._unsub = async_track_state_change_event(
                self.hass,
                list(entity_ids),
                self._async_state_changed,
            )

    @callback
    async def _async_state_changed(self, event) -> None:
        await self.async_refresh()

    def _normalize_flows(self, raw_flows: list[dict]) -> list[FlowDefinition]:
        flows: list[FlowDefinition] = []
        for item in raw_flows:
            if not isinstance(item, dict):
                continue

            name = item.get(CONF_NAME)
            target = item.get(CONF_TARGET, DEFAULT_TARGET) or DEFAULT_TARGET
            if not name:
                continue

            flows.append(
                FlowDefinition(
                    name=name,
                    target=target,
                    power_sensor=item.get(CONF_POWER_SENSOR),
                    power_import_sensor=item.get(CONF_POWER_IMPORT_SENSOR),
                    power_export_sensor=item.get(CONF_POWER_EXPORT_SENSOR),
                    invert_power_sensor=item.get(CONF_INVERT_POWER_SENSOR, False),
                )
            )

        return flows

    def _extract_value(self, entity_id: str | None) -> float:
        if not entity_id:
            return 0.0

        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return 0.0

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return 0.0

    def _calculate_flow_value(self, flow: FlowDefinition) -> float:
        if flow.power_import_sensor or flow.power_export_sensor:
            import_value = self._extract_value(flow.power_import_sensor)
            export_value = self._extract_value(flow.power_export_sensor)
            return import_value - export_value

        value = self._extract_value(flow.power_sensor)
        if flow.invert_power_sensor:
            return -value

        return value

    @staticmethod
    def _slug_topic_part(value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    def _publish_mqtt(self, groups: dict[str, float], connection_values: dict[str, dict]) -> None:
        if not self.mqtt_root:
            return

        from homeassistant.components.mqtt import async_publish

        root = self.mqtt_root.rstrip("/")
        for group_name, group_value in groups.items():
            topic = f"{root}/groups/{self._slug_topic_part(group_name)}"
            async_publish(self.hass, topic, group_value)

        for group_name, group_value in groups.items():
            topic = f"{root}/{self._slug_topic_part(group_name)}"
            async_publish(self.hass, topic, group_value)

        if self.mqtt_expose_connections:
            for conn_data in connection_values.values():
                source = self._slug_topic_part(conn_data["source"])
                target = self._slug_topic_part(conn_data["target"])
                topic = f"{root}/{source}_to_{target}"
                async_publish(self.hass, topic, conn_data["value"])

    async def _async_update_data(self) -> dict:
        if not self._flows:
            return {"groups": {}, "connections": {}, "leftover_name": self.leftover_name}

        groups: dict[str, float] = {}
        connection_values: dict[str, dict] = {}

        for flow in self._flows:
            connection_key = f"{flow.name}|{flow.target}"
            value = self._calculate_flow_value(flow)

            connection_values[connection_key] = {
                "source": flow.name,
                "target": flow.target,
                "value": value,
            }

            groups.setdefault(flow.name, 0.0)
            groups.setdefault(flow.target, 0.0)
            groups[flow.name] += value
            groups[flow.target] -= value

        self._publish_mqtt(groups, connection_values)

        return {
            "groups": groups,
            "connections": connection_values,
            "leftover_name": self.leftover_name,
        }
