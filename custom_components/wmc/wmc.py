import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

from .const import DOMAIN, CONF_SENSOR_INDOOR_TEMP, CONF_SENSOR_INDOOR_HUMIDITY, CONF_SENSOR_OUTDOOR_TEMP, CONF_SENSOR_OUTDOOR_HUMIDITY, CONF_LOW_SPEED, CONF_HIGH_SPEED, CONF_DELTA_TRIGGER, CONF_TARGET_OFFSET, CONF_MIN_ON_TIME, CONF_MAX_ON_TIME, CONF_SAMPLE_INTERVAL, CONF_MIN_HUMIDITY, CONF_UNIQUE_ID

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_SENSOR_INDOOR_TEMP): cv.entity_id,
    vol.Required(CONF_SENSOR_INDOOR_HUMIDITY): cv.entity_id,
    vol.Required(CONF_SENSOR_OUTDOOR_TEMP): cv.entity_id,
    vol.Required(CONF_SENSOR_OUTDOOR_HUMIDITY): cv.entity_id,
    vol.Required(CONF_LOW_SPEED): cv.entity_id,
    vol.Required(CONF_HIGH_SPEED): cv.entity_id,
    vol.Optional(CONF_DELTA_TRIGGER, default=3): cv.positive_int,
    vol.Optional(CONF_TARGET_OFFSET, default=3): cv.positive_int,
    vol.Optional(CONF_MIN_ON_TIME, default="00:05:00"): cv.time_period,
    vol.Optional(CONF_MAX_ON_TIME, default="02:00:00"): cv.time_period,
    vol.Optional(CONF_SAMPLE_INTERVAL, default="00:05:00"): cv.time_period,
    vol.Optional(CONF_MIN_HUMIDITY, default=30): cv.positive_int,
    vol.Optional(CONF_UNIQUE_ID): cv.string,
})

async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None):
    """Set up the WMC platform."""
    async_add_entities([WMC(hass, config)])

class WMC(Entity):
    """Representation of the WMC."""

    def __init__(self, hass: HomeAssistantType, config: ConfigType):
        """Initialize the WMC."""
        self._hass = hass
        self._config = config
        self._unique_id = config.get(CONF_UNIQUE_ID)
        # Other initializations...

    @property
    def name(self):
        """Return the name of the device."""
        return self._config.get(CONF_UNIQUE_ID, "WMC")

    @property
    def unique_id(self):
        """Return the unique ID of the device."""
        return self._unique_id
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