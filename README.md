# Power Flow Integration

Home Assistant custom integration for calculating power flows between named groups and a default `grid` target.

## Features

- Configure power devices/groups in the UI via config flow
- Support single signed power sensors or dual import/export sensors
- Calculate per-group raw power and per-connection flows
- Expose leftover/grid balance as a sensor
- Optional MQTT reporting when `mqtt_root` is configured
- Optional MQTT exposure of connection sensors

## Configuration

Install this integration as a custom component in `custom_components/power_flow`.

### Flow definitions

Configure the integration through Home Assistant's UI config flow. Use comma-separated lines in the flow definition text field:

```
Kitchen, grid, sensor.kitchen_power
EV Charger, grid, sensor.ev_power_import, sensor.ev_power_export
Battery, EV Charger, sensor.battery_power
```

- `name`: group or device name
- `target`: destination group/device name, default is `grid`
- `power_sensor`: single signed power sensor, or
- `power_import_sensor` and `power_export_sensor`

## MQTT

If `mqtt_root` is set in the config entry, the integration will publish MQTT updates under that topic root.

Published topics are flat under `mqtt_root`:

- `mqtt_root/<group_name>` for group power values
- `mqtt_root/<source>_to_<target>` for per-connection values when connection MQTT exposure is enabled

The config flow exposes an option to enable MQTT publishing for connection sensors.