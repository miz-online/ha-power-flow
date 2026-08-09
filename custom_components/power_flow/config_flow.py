from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ADD_ANOTHER,
    CONF_DEVICES,
    CONF_EDIT_DEVICES,
    CONF_LEFTOVER_NAME,
    CONF_MQTT_EXPOSE_CONNECTIONS,
    CONF_MQTT_ROOT,
    CONF_POWER_EXPORT_SENSOR,
    CONF_POWER_IMPORT_SENSOR,
    CONF_POWER_SENSOR,
    CONF_INVERT_POWER_SENSOR,
    CONF_TARGET,
    DEFAULT_INVERT_POWER_SENSOR,
    DEFAULT_LEFTOVER_NAME,
    DEFAULT_MQTT_EXPOSE_CONNECTIONS,
    DEFAULT_TARGET,
    DOMAIN,
)


class PowerFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._config_data: dict[str, str | bool] = {}
        self._devices: list[dict[str, str | bool | None]] = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config_data = {
                CONF_LEFTOVER_NAME: user_input.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
                CONF_MQTT_ROOT: user_input.get(CONF_MQTT_ROOT, ""),
                CONF_MQTT_EXPOSE_CONNECTIONS: user_input.get(
                    CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
                ),
            }
            return await self.async_step_flow()

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_config_schema(user_input),
            errors=errors,
        )

    async def async_step_flow(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                device = self._validate_device_input(user_input)
            except ValueError as err:
                errors["base"] = err.args[0]
            else:
                self._devices.append(device)
                if user_input.get(CONF_ADD_ANOTHER, False):
                    return self.async_show_form(
                        step_id="flow",
                        data_schema=self._get_flow_schema({CONF_ADD_ANOTHER: True}),
                        errors={},
                    )

                return self.async_create_entry(
                    title="Power Flow",
                    data={
                        CONF_DEVICES: self._devices,
                        CONF_LEFTOVER_NAME: self._config_data[CONF_LEFTOVER_NAME],
                        CONF_MQTT_ROOT: self._config_data[CONF_MQTT_ROOT],
                        CONF_MQTT_EXPOSE_CONNECTIONS: self._config_data[CONF_MQTT_EXPOSE_CONNECTIONS],
                    },
                )

        return self.async_show_form(
            step_id="flow",
            data_schema=self._get_flow_schema(user_input),
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
            }
        )

    @staticmethod
    def _get_flow_schema(user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_NAME: "",
            CONF_TARGET: DEFAULT_TARGET,
            CONF_POWER_SENSOR: "",
            CONF_INVERT_POWER_SENSOR: DEFAULT_INVERT_POWER_SENSOR,
            CONF_POWER_IMPORT_SENSOR: "",
            CONF_POWER_EXPORT_SENSOR: "",
            CONF_ADD_ANOTHER: True,
        }
        if user_input is not None:
            defaults.update(user_input)

        for key in (CONF_POWER_SENSOR, CONF_POWER_IMPORT_SENSOR, CONF_POWER_EXPORT_SENSOR):
            if defaults.get(key) is None:
                defaults[key] = ""

        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                vol.Optional(CONF_TARGET, default=defaults[CONF_TARGET]): str,
                vol.Optional(
                    CONF_POWER_SENSOR,
                    default=defaults[CONF_POWER_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_INVERT_POWER_SENSOR,
                    default=defaults[CONF_INVERT_POWER_SENSOR],
                ): bool,
                vol.Optional(
                    CONF_POWER_IMPORT_SENSOR,
                    default=defaults[CONF_POWER_IMPORT_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_POWER_EXPORT_SENSOR,
                    default=defaults[CONF_POWER_EXPORT_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_ADD_ANOTHER, default=defaults[CONF_ADD_ANOTHER]): bool,
            }
        )

    @staticmethod
    def _validate_device_input(user_input: dict) -> dict[str, str | None]:
        name = user_input.get(CONF_NAME, "").strip()
        if not name:
            raise ValueError("name_required")

        target = user_input.get(CONF_TARGET, DEFAULT_TARGET) or DEFAULT_TARGET
        power_sensor = user_input.get(CONF_POWER_SENSOR) or None
        invert_power_sensor = user_input.get(CONF_INVERT_POWER_SENSOR, DEFAULT_INVERT_POWER_SENSOR)
        power_import_sensor = user_input.get(CONF_POWER_IMPORT_SENSOR) or None
        power_export_sensor = user_input.get(CONF_POWER_EXPORT_SENSOR) or None

        if power_sensor and (power_import_sensor or power_export_sensor):
            raise ValueError("device_conflict")

        if power_sensor:
            return {
                CONF_NAME: name,
                CONF_TARGET: target,
                CONF_POWER_SENSOR: power_sensor,
                CONF_INVERT_POWER_SENSOR: bool(invert_power_sensor),
            }

        if not power_import_sensor or not power_export_sensor:
            raise ValueError("device_missing")

        return {
            CONF_NAME: name,
            CONF_TARGET: target,
            CONF_POWER_IMPORT_SENSOR: power_import_sensor,
            CONF_POWER_EXPORT_SENSOR: power_export_sensor,
            CONF_INVERT_POWER_SENSOR: bool(invert_power_sensor),
        }


class PowerFlowOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry
        self._config_data: dict[str, str | bool] = {}
        self._devices: list[dict[str, str | bool | None]] = []
        self._pending_devices: list[dict[str, str | bool | None]] = list(
            self.config_entry.data.get(CONF_DEVICES, [])
        )

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_EDIT_DEVICES, False):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_DEVICES: self.config_entry.data.get(CONF_DEVICES, []),
                        CONF_LEFTOVER_NAME: user_input.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
                        CONF_MQTT_ROOT: user_input.get(CONF_MQTT_ROOT, ""),
                        CONF_MQTT_EXPOSE_CONNECTIONS: user_input.get(
                            CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
                        ),
                    },
                )
                return self.async_create_entry(title="", data={})

            self._config_data = {
                CONF_LEFTOVER_NAME: user_input.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
                CONF_MQTT_ROOT: user_input.get(CONF_MQTT_ROOT, ""),
                CONF_MQTT_EXPOSE_CONNECTIONS: user_input.get(
                    CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
                ),
            }
            self._devices = []
            self._pending_devices = list(self.config_entry.data.get(CONF_DEVICES, []))
            return await self.async_step_flow()

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(user_input),
            errors=errors,
        )

    async def async_step_flow(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                device = PowerFlowConfigFlow._validate_device_input(user_input)
            except ValueError as err:
                errors["base"] = err.args[0]
            else:
                self._devices.append(device)
                if user_input.get(CONF_ADD_ANOTHER, False):
                    return self.async_show_form(
                        step_id="flow",
                        data_schema=self._get_flow_schema(self._next_device_defaults()),
                        errors={},
                    )

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        CONF_DEVICES: self._devices,
                        CONF_LEFTOVER_NAME: self._config_data[CONF_LEFTOVER_NAME],
                        CONF_MQTT_ROOT: self._config_data[CONF_MQTT_ROOT],
                        CONF_MQTT_EXPOSE_CONNECTIONS: self._config_data[CONF_MQTT_EXPOSE_CONNECTIONS],
                    },
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="flow",
            data_schema=self._get_flow_schema(self._next_device_defaults()),
            errors=errors,
        )

    def _get_options_schema(self, user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_LEFTOVER_NAME: self.config_entry.data.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
            CONF_MQTT_ROOT: self.config_entry.data.get(CONF_MQTT_ROOT, ""),
            CONF_MQTT_EXPOSE_CONNECTIONS: self.config_entry.data.get(
                CONF_MQTT_EXPOSE_CONNECTIONS, DEFAULT_MQTT_EXPOSE_CONNECTIONS
            ),
            CONF_EDIT_DEVICES: False,
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
                vol.Optional(CONF_EDIT_DEVICES, default=defaults[CONF_EDIT_DEVICES]): bool,
            }
        )

    @staticmethod
    def _get_flow_schema(user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_NAME: "",
            CONF_TARGET: DEFAULT_TARGET,
            CONF_POWER_SENSOR: "",
            CONF_INVERT_POWER_SENSOR: DEFAULT_INVERT_POWER_SENSOR,
            CONF_POWER_IMPORT_SENSOR: "",
            CONF_POWER_EXPORT_SENSOR: "",
            CONF_ADD_ANOTHER: True,
        }
        if user_input is not None:
            defaults.update(user_input)

        for key in (CONF_POWER_SENSOR, CONF_POWER_IMPORT_SENSOR, CONF_POWER_EXPORT_SENSOR):
            if defaults.get(key) is None:
                defaults[key] = ""

        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                vol.Optional(CONF_TARGET, default=defaults[CONF_TARGET]): str,
                vol.Optional(
                    CONF_POWER_SENSOR,
                    default=defaults[CONF_POWER_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_INVERT_POWER_SENSOR,
                    default=defaults[CONF_INVERT_POWER_SENSOR],
                ): bool,
                vol.Optional(
                    CONF_POWER_IMPORT_SENSOR,
                    default=defaults[CONF_POWER_IMPORT_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_POWER_EXPORT_SENSOR,
                    default=defaults[CONF_POWER_EXPORT_SENSOR],
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_ADD_ANOTHER, default=defaults[CONF_ADD_ANOTHER]): bool,
            }
        )

    def _next_device_defaults(self) -> dict[str, str | None]:
        if self._pending_devices:
            return self._pending_devices.pop(0)
        return {}
