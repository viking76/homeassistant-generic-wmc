"""
Adds support for generic dew point WMC units.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.generic_dew_point_wmc/
"""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Generic WMC"

CONF_HUMIDIFIER = "humidifier"
CONF_SENSOR = "target_sensor"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_TARGET_HUMIDITY = "target_humidity"
CONF_MIN_DUR = "min_cycle_duration"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_WET_TOLERANCE = "wet_tolerance"
CONF_KEEP_ALIVE = "keep_alive"
CONF_INITIAL_STATE = "initial_state"
CONF_AWAY_HUMIDITY = "away_humidity"
CONF_AWAY_FIXED = "away_fixed"
CONF_STALE_DURATION = "sensor_stale_duration"
CONF_LOW_SPEED = "low_speed"
CONF_HIGH_SPEED = "high_speed"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HUMIDIFIER): cv.entity_id,
        vol.Required(CONF_SENSOR): cv.entity_id,
        vol.Optional(CONF_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_MAX_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_TARGET_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_MIN_DUR): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_DRY_TOLERANCE, default=3): vol.Coerce(float),
        vol.Optional(CONF_WET_TOLERANCE, default=3): vol.Coerce(float),
        vol.Optional(CONF_KEEP_ALIVE): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_INITIAL_STATE): cv.boolean,
        vol.Optional(CONF_AWAY_HUMIDITY): vol.Coerce(int),
        vol.Optional(CONF_AWAY_FIXED): cv.boolean,
        vol.Optional(CONF_STALE_DURATION): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_LOW_SPEED): cv.entity_id,
        vol.Optional(CONF_HIGH_SPEED): cv.entity_id,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the WMC platform."""
    async_add_entities([WMCEntity(hass, config)])

class WMCEntity(ClimateEntity, RestoreEntity):
    """Representation of a WMC device."""

    def __init__(self, hass, config):
        """Initialize the WMC device."""
        self._hass = hass
        self._name = config.get(CONF_NAME)
        self._humidifier_entity_id = config[CONF_HUMIDIFIER]
        self._sensor_entity_id = config[CONF_SENSOR]
        self._min_humidity = config.get(CONF_MIN_HUMIDITY, 30)
        self._max_humidity = config.get(CONF_MAX_HUMIDITY, 50)
        self._target_humidity = config.get(CONF_TARGET_HUMIDITY, 40)
        self._low_speed_entity_id = config.get(CONF_LOW_SPEED)
        self._high_speed_entity_id = config.get(CONF_HIGH_SPEED)

        self._current_humidity = None
        self._hvac_mode = HVACMode.OFF
        self._supported_features = ClimateEntityFeature.TARGET_HUMIDITY

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
        return self._supported_features

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
        return self._max_humidity

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state:
            self._target_humidity = state.attributes.get("humidity", self._target_humidity)

        async_track_state_change_event(
            self._hass, [self._sensor_entity_id], self._async_sensor_changed
        )

    @callback
    def _async_sensor_changed(self, event):
        """Handle sensor state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        try:
            self._current_humidity = float(new_state.state)
        except ValueError:
            return

        self.async_write_ha_state()
        self._control_humidifier()

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
                if self._current_humidity < self._min_humidity:
                    await self._hass.services.async_call(
                        "homeassistant", "turn_on", {"entity_id": self._high_speed_entity_id}
                    )
                else:
                    await self._hass.services.async_call(
                        "homeassistant", "turn_on", {"entity_id": self._low_speed_entity_id}
                    )
            else:
                await self._hass.services.async_call(
                    "homeassistant", "turn_off", {"entity_id": self._humidifier_entity_id}
                )
        elif state == "off":
            await self._hass.services.async_call(
                "homeassistant", "turn_off", {"entity_id": self._humidifier_entity_id}
            )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()
