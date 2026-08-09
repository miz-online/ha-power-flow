from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEVICES,
    CONF_FLOWS_TEXT,
    CONF_LEFTOVER_NAME,
    CONF_MQTT_EXPOSE_CONNECTIONS,
    CONF_MQTT_ROOT,
    CONF_POWER_EXPORT_SENSOR,
    CONF_POWER_IMPORT_SENSOR,
    CONF_POWER_SENSOR,
    CONF_TARGET,
    DEFAULT_LEFTOVER_NAME,
    DEFAULT_MQTT_EXPOSE_CONNECTIONS,
    DEFAULT_TARGET,
    DOMAIN,
)


class PowerFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                devices = self._parse_flow_definitions(user_input[CONF_FLOWS_TEXT])
            except ValueError:
                errors[CONF_FLOWS_TEXT] = "invalid_flow_text"
            else:
                if not devices:
                    errors[CONF_FLOWS_TEXT] = "empty_flow_text"

            if not errors:
                return self.async_create_entry(
                    title="Power Flow",
                    data={
                        CONF_DEVICES: devices,
                        CONF_LEFTOVER_NAME: user_input.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
                        CONF_MQTT_ROOT: user_input.get(CONF_MQTT_ROOT, ""),
                        CONF_MQTT_EXPOSE_CONNECTIONS: user_input.get(
                            CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_config_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerFlowOptionsFlowHandler(config_entry)

    @staticmethod
    @callback
    def _get_config_schema(user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_LEFTOVER_NAME: DEFAULT_LEFTOVER_NAME,
            CONF_MQTT_ROOT: "",
            CONF_MQTT_EXPOSE_CONNECTIONS: DEFAULT_MQTT_EXPOSE_CONNECTIONS,
            CONF_FLOWS_TEXT: "",
        }
        if user_input is not None:
            defaults.update(user_input)

        return vol.Schema(
            {
                vol.Optional(CONF_LEFTOVER_NAME, default=defaults[CONF_LEFTOVER_NAME]): str,
                vol.Optional(CONF_MQTT_ROOT, default=defaults[CONF_MQTT_ROOT]): str,
                vol.Optional(
                    CONF_MQTT_EXPOSE_CONNECTIONS,
                    default=defaults[CONF_MQTT_EXPOSE_CONNECTIONS],
                ): bool,
                vol.Optional(CONF_FLOWS_TEXT, default=defaults[CONF_FLOWS_TEXT]): str,
            }
        )

    @staticmethod
    def _parse_flow_definitions(flow_text: str) -> list[dict]:
        devices: list[dict] = []
        for raw_line in flow_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [part.strip() for part in line.split(",")]
            if len(parts) not in (3, 4):
                raise ValueError("Each flow must have 3 or 4 comma-separated values")

            name = parts[0]
            target = parts[1] or DEFAULT_TARGET
            if not name:
                raise ValueError("Each flow must define a name")

            if len(parts) == 3:
                devices.append(
                    {
                        CONF_NAME: name,
                        CONF_TARGET: target,
                        CONF_POWER_SENSOR: parts[2],
                    }
                )
            else:
                devices.append(
                    {
                        CONF_NAME: name,
                        CONF_TARGET: target,
                        CONF_POWER_IMPORT_SENSOR: parts[2] or None,
                        CONF_POWER_EXPORT_SENSOR: parts[3] or None,
                    }
                )

        return devices


class PowerFlowOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                devices = PowerFlowConfigFlow._parse_flow_definitions(user_input[CONF_FLOWS_TEXT])
            except ValueError:
                errors[CONF_FLOWS_TEXT] = "invalid_flow_text"
            else:
                if not devices:
                    errors[CONF_FLOWS_TEXT] = "empty_flow_text"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_DEVICES: devices,
                        CONF_LEFTOVER_NAME: user_input.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
                        CONF_MQTT_ROOT: user_input.get(CONF_MQTT_ROOT, ""),
                        CONF_MQTT_EXPOSE_CONNECTIONS: user_input.get(
                            CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
                        ),
                    },
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(user_input),
            errors=errors,
        )

    def _get_options_schema(self, user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_LEFTOVER_NAME: self.config_entry.data.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
            CONF_MQTT_ROOT: self.config_entry.data.get(CONF_MQTT_ROOT, ""),
            CONF_MQTT_EXPOSE_CONNECTIONS: self.config_entry.data.get(
                CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
            ),
            CONF_FLOWS_TEXT: self._serialize_devices(self.config_entry.data.get(CONF_DEVICES, [])),
        }
        if user_input is not None:
            defaults.update(user_input)

        return vol.Schema(
            {
                vol.Optional(CONF_LEFTOVER_NAME, default=defaults[CONF_LEFTOVER_NAME]): str,
                vol.Optional(CONF_MQTT_ROOT, default=defaults[CONF_MQTT_ROOT]): str,
                vol.Optional(
                    CONF_MQTT_EXPOSE_CONNECTIONS,
                    default=defaults[CONF_MQTT_EXPOSE_CONNECTIONS],
                ): bool,
                vol.Optional(CONF_FLOWS_TEXT, default=defaults[CONF_FLOWS_TEXT]): str,
            }
        )

    @staticmethod
    def _serialize_devices(devices: list[dict]) -> str:
        lines: list[str] = []
        for device in devices:
            if device.get(CONF_POWER_SENSOR):
                lines.append(
                    f"{device[CONF_NAME]},{device[CONF_TARGET]},{device[CONF_POWER_SENSOR]}"
                )
            else:
                lines.append(
                    f"{device[CONF_NAME]},{device[CONF_TARGET]},{device.get(CONF_POWER_IMPORT_SENSOR, '')},{device.get(CONF_POWER_EXPORT_SENSOR, '')}"
                )
        return "\n".join(lines)
