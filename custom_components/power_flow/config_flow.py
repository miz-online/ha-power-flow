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
    CONF_DEVICES,
    CONF_FLOWS_TEXT,
    CONF_NAME,
    CONF_TARGET,
    CONF_DEVICE_TYPE,
    CONF_POWER_SENSOR,
    CONF_INVERT_POWER_SENSOR,
    CONF_POWER_IMPORT_SENSOR,
    CONF_POWER_EXPORT_SENSOR,
    DEFAULT_TARGET,
    DEVICE_TYPE_SINGLE,
    DOMAIN,
)


class PowerFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            flows_text = user_input.get(CONF_FLOWS_TEXT, "") or ""
            devices = PowerFlowConfigFlow._devices_from_names(flows_text)
            return self.async_create_entry(
                title="Power Flow",
                data={
                    CONF_DEVICES: devices,
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
            CONF_FLOWS_TEXT: "",
        }
        if user_input is not None:
            defaults.update(user_input)

        flows_text_schema = str
        if selector is not None and hasattr(selector, "TextSelector") and hasattr(selector, "TextSelectorConfig"):
            flows_text_schema = selector.TextSelector(selector.TextSelectorConfig())

        return vol.Schema(
            {
                vol.Optional(CONF_FLOWS_TEXT, default=defaults[CONF_FLOWS_TEXT]): flows_text_schema,

            }
        )

    @staticmethod
    def _parse_flow_names(flows_text: str) -> list[str]:
        return [name.strip() for name in flows_text.splitlines() if name.strip()]

    @staticmethod
    def _device_placeholder(name: str) -> dict[str, str | bool | None]:
        return {
            CONF_NAME: name,
            CONF_TARGET: DEFAULT_TARGET,
            CONF_DEVICE_TYPE: DEVICE_TYPE_SINGLE,
            CONF_POWER_SENSOR: "",
            CONF_INVERT_POWER_SENSOR: False,
            CONF_POWER_IMPORT_SENSOR: "",
            CONF_POWER_EXPORT_SENSOR: "",
        }

    @staticmethod
    def _devices_from_names(flows_text: str) -> list[dict[str, str | bool | None]]:
        return [PowerFlowConfigFlow._device_placeholder(name) for name in PowerFlowConfigFlow._parse_flow_names(flows_text)]

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

    async def async_step_init(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            flows_text = user_input.get(CONF_FLOWS_TEXT, "") or ""
            devices = self._devices_from_names(flows_text, self._config_entry.data.get(CONF_DEVICES, []))
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={
                    CONF_DEVICES: devices,
                },
            )
            coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
            if coordinator is not None:
                coordinator._flows = coordinator._normalize_flows(devices)
                coordinator._setup_listeners()
                await coordinator.async_refresh()
            return self.async_create_entry(title="", data={})

        current_devices = self._config_entry.data.get(CONF_DEVICES, [])
        flows_text = "\n".join(dev.get(CONF_NAME, "") for dev in current_devices)
        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema({CONF_FLOWS_TEXT: flows_text}),
            errors=errors,
        )

    def _get_options_schema(self, user_input: dict | None = None) -> vol.Schema:
        defaults = {
            CONF_FLOWS_TEXT: "",
        }
        if user_input is not None:
            defaults.update(user_input)

        flows_text_schema = str
        if selector is not None and hasattr(selector, "TextSelector") and hasattr(selector, "TextSelectorConfig"):
            flows_text_schema = selector.TextSelector(selector.TextSelectorConfig())

        return vol.Schema(
            {
                vol.Optional(CONF_FLOWS_TEXT, default=defaults[CONF_FLOWS_TEXT]): flows_text_schema,
            }
        )

    @staticmethod
    def _devices_from_names(flows_text: str, existing_devices: list[dict[str, str | bool | None]]) -> list[dict[str, str | bool | None]]:
        existing_by_name = {
            device.get(CONF_NAME, ""): device
            for device in existing_devices
            if device.get(CONF_NAME)
        }
        names = [name.strip() for name in flows_text.splitlines() if name.strip()]
        devices: list[dict[str, str | bool | None]] = []
        for name in names:
            if name in existing_by_name:
                devices.append(existing_by_name[name])
            else:
                devices.append(PowerFlowConfigFlow._device_placeholder(name))
        return devices
