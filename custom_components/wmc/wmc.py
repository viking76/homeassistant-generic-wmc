from homeassistant.components.climate import (
    ClimateEntity
)
from homeassistant.components.climate.const import (
    HVACMode
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS
)
from homeassistant.helpers.event import async_track_state_change_event

class WMCEntity(ClimateEntity):
    """Representation of a WMC device."""

    def __init__(self, hass, config):
        """Initialize the WMC device."""
        self._hass = hass
        self._name = config.get("name")
        self._sensor_indoor_temp = config.get("sensor_indoor_temp")
        self._sensor_indoor_humidity = config.get("sensor_indoor_humidity")
        self._sensor_outdoor_temp = config.get("sensor_outdoor_temp")
        self._sensor_outdoor_humidity = config.get("sensor_outdoor_humidity")
        self._low_speed = config.get("low_speed")
        self._high_speed = config.get("high_speed")
        self._target_humidity = config.get("target_humidity", 40)
        self._min_humidity = config.get("min_humidity", 30)
        self._current_humidity = None
        self._hvac_mode = HVACMode.OFF

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def hvac_mode(self):
        """Return the current operation mode."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return [HVACMode.OFF, HVACMode.FAN_ONLY]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_HUMIDITY

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._target_humidity

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        return self._min_humidity

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        return self._target_humidity

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        async_track_state_change_event(
            self._hass, [self._sensor_indoor_temp, self._sensor_indoor_humidity,
                         self._sensor_outdoor_temp, self._sensor_outdoor_humidity], 
            self._async_sensor_changed
        )

    async def _async_sensor_changed(self, event):
        """Handle sensor state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        try:
            self._current_humidity = float(new_state.state)
        except ValueError:
            return

        await self._control_humidifier()

    async def _control_humidifier(self):
        """Control the humidifier based on the target humidity."""
        if self._current_humidity is None:
            return
        if self._current_humidity < self._target_humidity:
            await self._set_humidifier_state("on")
        else:
            await self._set_humidifier_state("off")

    async def _set_humidifier_state(self, state):
        """Set the state of the humidifier."""
        if state == "on":
            if self._current_humidity < self._target_humidity:
                await self._hass.services.async_call(
                    "homeassistant", "turn_on", {"entity_id": self._high_speed}
                )
            else:
                await self._hass.services.async_call(
                    "homeassistant", "turn_on", {"entity_id": self._low_speed}
                )
        elif state == "off":
            await self._hass.services.async_call(
                "homeassistant", "turn_off", {"entity_id": self._low_speed}
            )
            await self._hass.services.async_call(
                "homeassistant", "turn_off", {"entity_id": self._high_speed}
            )

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the WMC platform."""
    async_add_entities([WMCEntity(hass, config)])
