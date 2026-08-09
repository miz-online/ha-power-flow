## Plan: Home Assistant HACS Power Flow Integration

TL;DR: Build a new Home Assistant custom integration named `power_flow` that consumes YAML-configured power sensors, resolves connections between named groups and grid, computes raw group power and leftover, exposes sensors, and optionally publishes MQTT updates under a configurable root.

**Steps**
1. Scaffold the integration and HACS packaging.
   - Create a repository layout with `power_flow/manifest.json`, `power_flow/__init__.py`, `power_flow/sensor.py`, `power_flow/const.py`, `hacs.json`, and `README.md`.
   - The integration domain will be `power_flow` and the repository will be HACS-ready.
2. Define configuration schema via config flow.
   - Offer configuration entirely through Home Assistant UI, avoiding global `configuration.yaml` edits.
   - Configure devices/groups with `name`, `target` (default `grid`), and power sensor references.
   - Support: single signed power sensor or dual import/export sensors per configured entity.
   - Add optional `leftover_name` and `mqtt_root`; MQTT is active when a root is configured.
3. Model connections and raw power calculation.
   - Treat each configured entity as a directed flow from its named group to its configured target group.
   - Positive power means consumption from the target into the source; negative means export toward the target.
   - Compute each named group’s raw power by summing incoming flows for the group and subtracting outgoing flows.
   - Expose the grid/remainder node as the configured leftover sensor.
   - Provide flow sensors for each connection between two groups/devices, in addition to per-group raw usage sensors.
4. Implement sensor platform and integration device.
   - Use `async_setup` and config flow to build source sensor subscriptions and integration config.
   - Use a single `DeviceInfo` device representing the `power_flow` integration.
   - Create sensor entities for each distinct group name, each connection flow, and leftover.
   - Listen for source sensor state changes and recompute all sensor values.
   - Publish MQTT state updates when `mqtt_root` is configured, using HA’s MQTT support.
5. Add Home Assistant and HACS metadata.
   - `manifest.json` with `domain`, `name`, `version`, `documentation`, `integration_type`, `iot_class`, `dependencies` (including `mqtt` if used), and `quality_scale`.
   - `hacs.json` describing the integration for HACS discovery.
6. Validate and verify.
   - Test the integration via Home Assistant with sample YAML.
   - Confirm sensors appear, values update after source power changes, device is created, and MQTT topics publish if enabled.

**Verification**
1. Add `power_flow:` YAML to Home Assistant `configuration.yaml` and restart.
2. Confirm the new `power_flow` device appears as an integration device with sensor entities for each name and leftover.
3. Change source power sensor states and verify calculated raw group values update.
4. If MQTT is enabled, verify messages appear under the configured root topic.

**Decisions**
- Use Home Assistant UI config flow instead of global YAML configuration whenever feasible.
- Implement both single signed sensors and dual import/export sensors for source entities.
- Represent the grid as a special connection target and map its net power to the leftover sensor.
- Use HA MQTT support instead of direct external MQTT libraries.

**Further Considerations**
1. If you want UI-based configuration later, the next phase should add `config_flow.py` and `options_flow.py`.
2. If you need named device-to-device mapping by actual `entity_id` instead of logical group names, that can be added after the core graph model is working.
3. Decide whether leftover should be a fixed `sensor.leftover` entity or a configurable name; the plan uses configurable name as requested.
