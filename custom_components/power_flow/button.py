from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_DEVICES, DEFAULT_TARGET, DEVICE_TYPE_SINGLE
from .data import PowerFlowCoordinator


class PowerFlowAddButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_name = "Power Flow: Add Device"
        self._attr_unique_id = f"{entry.entry_id}_add_device_button"

    @property
    def should_poll(self) -> bool:
        return False

    async def async_press(self) -> None:
        # Create a simple placeholder device so user can edit it later via Options
        entry = self._entry
        devices = list(entry.data.get(CONF_DEVICES, []))
        idx = len(devices) + 1
        new_device = {
            "name": f"New device {idx}",
            "target": DEFAULT_TARGET,
            "device_type": DEVICE_TYPE_SINGLE,
            "power_sensor": "",
            "invert_power_sensor": False,
        }

        new_data = dict(entry.data)
        new_data[CONF_DEVICES] = devices + [new_device]

        # Persist to config entry
        self.hass.config_entries.async_update_entry(entry, data=new_data)

        # Update coordinator if loaded
        coordinator: PowerFlowCoordinator | None = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is not None:
            coordinator._flows = coordinator._normalize_flows(new_data.get(CONF_DEVICES, []))
            coordinator._setup_listeners()
            await coordinator.async_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the Add Device button for a config entry."""
    async_add_entities([PowerFlowAddButton(hass, entry)])
