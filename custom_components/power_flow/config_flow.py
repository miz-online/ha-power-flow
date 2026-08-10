from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

try:
    from homeassistant.helpers import selector
except ImportError:
    selector = None

from .const import (
    CONF_ADD_ANOTHER,
    CONF_DEVICE_TYPE,
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
    DEVICE_TYPE_MULTI,
    DEVICE_TYPE_SINGLE,
    DOMAIN,
)


class PowerFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        pass

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Power Flow",
                data={
                    CONF_DEVICES: [],
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
            CONF_DEVICE_TYPE: DEVICE_TYPE_SINGLE,
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

        device_type_schema = vol.In([DEVICE_TYPE_SINGLE, DEVICE_TYPE_MULTI])
        power_sensor_schema = str
        if selector is not None:
            if hasattr(selector, "SelectSelector") and hasattr(selector, "SelectSelectorConfig"):
                device_type_schema = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": DEVICE_TYPE_SINGLE, "label": "Single power sensor"},
                            {"value": DEVICE_TYPE_MULTI, "label": "Import/export sensors"},
                        ]
                    )
                )
            if hasattr(selector, "EntitySelector") and hasattr(selector, "EntitySelectorConfig"):
                power_sensor_schema = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))

        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                vol.Required(
                    CONF_DEVICE_TYPE,
                    default=defaults[CONF_DEVICE_TYPE],
                ): device_type_schema,
                vol.Optional(CONF_TARGET, default=defaults[CONF_TARGET]): str,
                vol.Optional(
                    CONF_POWER_SENSOR,
                    default=defaults[CONF_POWER_SENSOR],
                ): power_sensor_schema,
                vol.Optional(
                    CONF_INVERT_POWER_SENSOR,
                    default=defaults[CONF_INVERT_POWER_SENSOR],
                ): bool,
                vol.Optional(
                    CONF_POWER_IMPORT_SENSOR,
                    default=defaults[CONF_POWER_IMPORT_SENSOR],
                ): power_sensor_schema,
                vol.Optional(
                    CONF_POWER_EXPORT_SENSOR,
                    default=defaults[CONF_POWER_EXPORT_SENSOR],
                ): power_sensor_schema,
                vol.Optional(CONF_ADD_ANOTHER, default=defaults[CONF_ADD_ANOTHER]): bool,
            }
        )

    @staticmethod
    def _validate_device_input(user_input: dict) -> dict[str, str | None]:
        name = user_input.get(CONF_NAME, "").strip()
        if not name:
            raise ValueError("name_required")

        target = user_input.get(CONF_TARGET, DEFAULT_TARGET) or DEFAULT_TARGET
        device_type = user_input.get(CONF_DEVICE_TYPE, DEVICE_TYPE_SINGLE)
        power_sensor = user_input.get(CONF_POWER_SENSOR) or None
        invert_power_sensor = user_input.get(CONF_INVERT_POWER_SENSOR, DEFAULT_INVERT_POWER_SENSOR)
        power_import_sensor = user_input.get(CONF_POWER_IMPORT_SENSOR) or None
        power_export_sensor = user_input.get(CONF_POWER_EXPORT_SENSOR) or None

        if device_type == DEVICE_TYPE_SINGLE:
            if not power_sensor:
                raise ValueError("single_sensor_required")
            if power_import_sensor or power_export_sensor:
                raise ValueError("device_conflict")
            return {
                CONF_NAME: name,
                CONF_TARGET: target,
                CONF_DEVICE_TYPE: device_type,
                CONF_POWER_SENSOR: power_sensor,
                CONF_INVERT_POWER_SENSOR: bool(invert_power_sensor),
            }

        if device_type == DEVICE_TYPE_MULTI:
            if not power_import_sensor or not power_export_sensor:
                raise ValueError("multi_sensor_required")
            if power_sensor:
                raise ValueError("device_conflict")
            return {
                CONF_NAME: name,
                CONF_TARGET: target,
                CONF_DEVICE_TYPE: device_type,
                CONF_POWER_IMPORT_SENSOR: power_import_sensor,
                CONF_POWER_EXPORT_SENSOR: power_export_sensor,
                CONF_INVERT_POWER_SENSOR: bool(invert_power_sensor),
            }

        raise ValueError("invalid_device_type")


class PowerFlowOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._config_data: dict[str, str | bool] = {}
        self._devices: list[dict[str, str | bool | None]] = []
        self._pending_devices: list[dict[str, str | bool | None]] = list(
            self._config_entry.data.get(CONF_DEVICES, [])
        )
        self._editing_index: int | None = None

    async def async_step_init(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_EDIT_DEVICES, False):
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={
                        CONF_DEVICES: self._config_entry.data.get(CONF_DEVICES, []),
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
            # Start with the existing devices list so we can edit in-place
            self._devices = list(self._config_entry.data.get(CONF_DEVICES, []))
            self._pending_devices = list(self._devices)
            self._editing_index = None
            return await self.async_step_edit_list()

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(user_input),
            errors=errors,
        )

    async def async_step_flow(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                device = PowerFlowConfigFlow._validate_device_input(user_input)
            except ValueError as err:
                errors["base"] = err.args[0]
            else:
                # If editing an existing device, replace it in-place
                if self._editing_index is not None and 0 <= self._editing_index < len(self._devices):
                    self._devices[self._editing_index] = device
                    self._editing_index = None
                else:
                    self._devices.append(device)
                if user_input.get(CONF_ADD_ANOTHER, False):
                    return self.async_show_form(
                        step_id="flow",
                        data_schema=PowerFlowConfigFlow._get_flow_schema(self._next_device_defaults()),
                        errors={},
                    )

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
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
            data_schema=PowerFlowConfigFlow._get_flow_schema(self._current_edit_defaults()),
            errors=errors,
        )

    def _get_options_schema(self, user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_LEFTOVER_NAME: self._config_entry.data.get(CONF_LEFTOVER_NAME, DEFAULT_LEFTOVER_NAME),
            CONF_MQTT_ROOT: self._config_entry.data.get(CONF_MQTT_ROOT, ""),
            CONF_MQTT_EXPOSE_CONNECTIONS: self._config_entry.data.get(
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

    def _next_device_defaults(self) -> dict[str, str | None]:
        if self._pending_devices:
            return self._pending_devices.pop(0)
        return {}

    def _current_edit_defaults(self) -> dict[str, str | None]:
        if self._editing_index is not None and 0 <= self._editing_index < len(self._devices):
            return self._devices[self._editing_index]
        return {}

    async def async_step_edit_list(self, user_input: dict | None = None):
        """Show a list of existing devices to edit or allow adding a new device."""
        errors: dict[str, str] = {}

        device_names = [d.get(CONF_NAME, "") for d in self._devices]
        options = ["__add_new__"] + device_names

        if user_input is not None:
            choice = user_input.get("select_device")
            if choice == "__add_new__":
                self._editing_index = None
                return await self.async_step_flow()

            # Find the first device matching the chosen name
            for idx, dev in enumerate(self._devices):
                if dev.get(CONF_NAME) == choice:
                    self._editing_index = idx
                    return await self.async_step_flow()

            errors["base"] = "invalid_selection"

        default = device_names[0] if device_names else "__add_new__"
        schema = vol.Schema({vol.Required("select_device", default=default): vol.In(options)})
        return self.async_show_form(step_id="edit_list", data_schema=schema, errors=errors)
