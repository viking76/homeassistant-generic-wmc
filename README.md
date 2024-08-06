# Generic WMC use (Dew Point)

This component adds support for a generic dew point-based hygrostat with two-speed ventilation control in Home Assistant. It helps in maintaining a comfortable indoor humidity level by controlling ventilation based on indoor and outdoor humidity and temperature.

## Features

- Dew point calculation for precise humidity control.
- Two-speed ventilation control (low and high).
- Adjustable parameters for custom humidity management.
- Integration with Home Assistant's sensor platform.

## Configuration

### Prerequisites

Ensure you have the following sensors set up in Home Assistant:

1. Indoor temperature sensor
2. Indoor humidity sensor
3. Outdoor temperature sensor
4. Outdoor humidity sensor
5. Two entities to control low and high-speed ventilation

### Installation

1. Copy the `generic_wmc.py` file to your `custom_components` directory in Home Assistant.
2. Add the following configuration to your `configuration.yaml` file:

```yaml
generic_wmc:
  - platform: generic_wmc
    name: "Living Room Hygrostat"
    sensor_indoor_temp: sensor.indoor_temperature
    sensor_indoor_humidity: sensor.indoor_humidity
    sensor_outdoor_temp: sensor.outdoor_temperature
    sensor_outdoor_humidity: sensor.outdoor_humidity
    low_speed: switch.low_speed_ventilation
    high_speed: switch.high_speed_ventilation
    delta_trigger: 3
    target_offset: 3
    min_on_time: 00:05:00
    max_on_time: 02:00:00
    sample_interval: 00:05:00
    min_humidity: 30
    unique_id: "living_room_hygrostat"
```

### Configuration Parameters

    name: Name of the hygrostat.
    sensor_indoor_temp: Entity ID of the indoor temperature sensor.
    sensor_indoor_humidity: Entity ID of the indoor humidity sensor.
    sensor_outdoor_temp: Entity ID of the outdoor temperature sensor.
    sensor_outdoor_humidity: Entity ID of the outdoor humidity sensor.
    low_speed: Entity ID for controlling low-speed ventilation.
    high_speed: Entity ID for controlling high-speed ventilation.
    delta_trigger: The dew point difference that triggers high-speed ventilation (default is 3°C).
    target_offset: Offset added to the outdoor dew point to set the dehumidification target.
    min_on_time: Minimum duration for which the ventilation stays on once triggered.
    max_on_time: Maximum duration for which the ventilation can stay on continuously.
    sample_interval: Interval at which the sensor readings are sampled.
    min_humidity: Minimum indoor humidity level.
    unique_id: Unique identifier for the hygrostat entity.

## Example

Below is an example configuration for a living room hygrostat:

```yaml

climate:
  - platform: generic_dew_point_wmc
    name: "Living Room Hygrostat"
    sensor_indoor_temp: sensor.living_room_temperature
    sensor_indoor_humidity: sensor.living_room_humidity
    sensor_outdoor_temp: sensor.outdoor_temperature
    sensor_outdoor_humidity: sensor.outdoor_humidity
    low_speed: switch.living_room_ventilation_low
    high_speed: switch.living_room_ventilation_high
    delta_trigger: 3
    target_offset: 3
    min_on_time: 00:05:00
    max_on_time: 02:00:00
    sample_interval: 00:05:00
    min_humidity: 30
    unique_id: "living_room_hygrostat"
```
## How it Works

    Initialization: The hygrostat reads the sensor values and initializes the internal state.
    Updating: At each sample interval, the hygrostat reads the current indoor and outdoor temperature and humidity values.
    Dew Point Calculation: It calculates the indoor and outdoor dew points using the temperature and humidity values.
    Ventilation Control:
        If the indoor dew point is higher than the target dew point (outdoor dew point + offset), it activates the appropriate ventilation speed based on the delta trigger.
        The ventilation remains on for at least the minimum on time and is turned off after the maximum on time if conditions are met.
        If the indoor humidity is below the minimum humidity, the ventilation is turned off.

## Notes

    Ensure that the sensor entity IDs are correct and that the sensors are providing valid data.
    Adjust the delta trigger and target offset according to your specific requirements for indoor humidity control.
    The component relies on the Home Assistant event loop for periodic updates, so make sure your Home Assistant instance is running smoothly.

### NO Support at this time

For more details about this platform, please refer to the Home Assistant documentation.


