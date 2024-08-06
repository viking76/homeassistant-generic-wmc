"""
Adds support for generic dew point WMC units.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.generic_dew_point_wmc/
"""
import asyncio
import collections
import math
from datetime import timedelta, datetime
import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNKNOWN, CONF_NAME, CONF_UNIQUE_ID
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["sensor"]

SAMPLE_DURATION = timedelta(minutes=15)

DEFAULT_NAME = "Generic Dew Point WMC"

CONF_SENSOR_INDOOR_TEMP = "sensor_indoor_temp"
CONF_SENSOR_INDOOR_HUMIDITY = "sensor_indoor_humidity"
CONF_SENSOR_OUTDOOR_TEMP = "sensor_outdoor_temp"
CONF_SENSOR_OUTDOOR_HUMIDITY = "sensor_outdoor_humidity"
CONF_LOW_SPEED = "low_speed"
CONF_HIGH_SPEED = "high_speed"
CONF_DELTA_TRIGGER = "delta_trigger"
CONF_TARGET_OFFSET = "target_offset"
CONF_MIN_ON_TIME = "min_on_time"
CONF_MAX_ON_TIME = "max_on_time"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_SAMPLE_INTERVAL = "sample_interval"

DEFAULT_DELTA_TRIGGER = 3
DEFAULT_TARGET_OFFSET = 3
DEFAULT_MIN_ON_TIME = timedelta(seconds=0)
DEFAULT_MAX_ON_TIME = timedelta(seconds=7200)
DEFAULT_SAMPLE_INTERVAL = timedelta(minutes=5)
DEFAULT_MIN_HUMIDITY = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SENSOR_INDOOR_TEMP): cv.entity_id,
        vol.Required(CONF_SENSOR_INDOOR_HUMIDITY): cv.entity_id,
        vol.Required(CONF_SENSOR_OUTDOOR_TEMP): cv.entity_id,
        vol.Required(CONF_SENSOR_OUTDOOR_HUMIDITY): cv.entity_id,
        vol.Required(CONF_LOW_SPEED): cv.entity_id,
        vol.Required(CONF_HIGH_SPEED): cv.entity_id,
        vol.Optional(CONF_DELTA_TRIGGER, default=DEFAULT_DELTA_TRIGGER): vol.Coerce(float),
        vol.Optional(CONF_TARGET_OFFSET, default=DEFAULT_TARGET_OFFSET): vol.Coerce(float),
        vol.Optional(CONF_MIN_ON_TIME, default=DEFAULT_MIN_ON_TIME): cv.time_period,
        vol.Optional(CONF_MAX_ON_TIME, default=DEFAULT_MAX_ON_TIME): cv.time_period,
        vol.Optional(CONF_SAMPLE_INTERVAL, default=DEFAULT_SAMPLE_INTERVAL): cv.time_period,
        vol.Optional(CONF_MIN_HUMIDITY, default=DEFAULT_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Generic Dew Point WMC platform."""
    name = config.get(CONF_NAME)
    sensor_indoor_temp = config.get(CONF_SENSOR_INDOOR_TEMP)
    sensor_indoor_humidity = config.get(CONF_SENSOR_INDOOR_HUMIDITY)
    sensor_outdoor_temp = config.get(CONF_SENSOR_OUTDOOR_TEMP)
    sensor_outdoor_humidity = config.get(CONF_SENSOR_OUTDOOR_HUMIDITY)
    low_speed = config.get(CONF_LOW_SPEED)
    high_speed = config.get(CONF_HIGH_SPEED)
    delta_trigger = config.get(CONF_DELTA_TRIGGER)
    target_offset = config.get(CONF_TARGET_OFFSET)
    min_on_time = config.get(CONF_MIN_ON_TIME)
    max_on_time = config.get(CONF_MAX_ON_TIME)
    sample_interval = config.get(CONF_SAMPLE_INTERVAL)
    min_humidity = config.get(CONF_MIN_HUMIDITY)
    unique_id = config.get(CONF_UNIQUE_ID)

    async_add_entities(
        [
            GenericDewPointWMC(
                hass,
                name,
                sensor_indoor_temp,
                sensor_indoor_humidity,
                sensor_outdoor_temp,
                sensor_outdoor_humidity,
                low_speed,
                high_speed,
                delta_trigger,
                target_offset,
                min_on_time,
                max_on_time,
                sample_interval,
                min_humidity,
                unique_id,
            )
        ]
    )

class GenericDewPointWMC(ClimateEntity):
    """Representation of a Generic Dew Point WMC device."""

    def __init__(
        self,
        hass,
        name,
        sensor_indoor_temp,
        sensor_indoor_humidity,
        sensor_outdoor_temp,
        sensor_outdoor_humidity,
        low_speed,
        high_speed,
        delta_trigger,
        target_offset,
        min_on_time,
        max_on_time,
        sample_interval,
        min_humidity,
        unique_id,
    ):
        """Initialize the WMC."""
        self.hass = hass
        self._name = name
        self.sensor_indoor_temp = sensor_indoor_temp
        self.sensor_indoor_humidity = sensor_indoor_humidity
        self.sensor_outdoor_temp = sensor_outdoor_temp
        self.sensor_outdoor_humidity = sensor_outdoor_humidity
        self.low_speed = low_speed
        self.high_speed = high_speed
        self.delta_trigger = delta_trigger
        self.target_offset = target_offset
        self.min_on_time = min_on_time
        self.max_on_time = max_on_time
        self.min_humidity = min_humidity
        self._unique_id = unique_id

        self.indoor_temp = None
        self.indoor_humidity = None
        self.outdoor_temp = None
        self.outdoor_humidity = None
        self.target = None
        sample_size = int(SAMPLE_DURATION / sample_interval)
        self.samples = collections.deque([], sample_size)
        self.min_on_timer = None
        self.max_on_timer = None

        self.indoor_dew_point = None
        self.outdoor_dew_point = None

        self._state = STATE_OFF
        self._icon = "mdi:water-percent"

        self._async_update()

        async_track_time_interval(hass, self._async_update, sample_interval)

    @callback
    def _async_update(self, now=None):
        try:
            self.update_sensor_data()
        except ValueError as ex:
            _LOGGER.warning(ex)
            return

        if self.min_on_timer and self.min_on_timer > datetime.now():
            _LOGGER.debug("Minimum time on not yet met for '%s'", self.name)
            return

        self.indoor_dew_point = self.calculate_dew_point(self.indoor_temp, self.indoor_humidity)
        self.outdoor_dew_point = self.calculate_dew_point(self.outdoor_temp, self.outdoor_humidity)

        if self.target and self.indoor_dew_point <= self.target:
            _LOGGER.debug("Dehumidifying target reached for '%s'", self.name)
            self.set_off()
            return

        if self.max_on_timer and self.max_on_timer < datetime.now():
            _LOGGER.debug("Max on timer reached for '%s'", self.name)
            self.set_off()
            return

        if self.indoor_humidity < self.min_humidity:
            _LOGGER.debug("Humidity '%s' is below minimum humidity '%s'", self.indoor_humidity, self.min_humidity)
            return

        if self.calc_delta(self.indoor_dew_point, self.outdoor_dew_point) >= self.delta_trigger:
            _LOGGER.debug("Humidity rise detected at '%s' with delta '%s'", self.name, self.calc_delta(self.indoor_dew_point, self.outdoor_dew_point))
            self.set_on()
            return

    def update_sensor_data(self):
        """Update local temperature and humidity states from source sensors."""
        sensor_indoor_temp = self.hass.states.get(self.sensor_indoor_temp)
        sensor_indoor_humidity = self.hass.states.get(self.sensor_indoor_humidity)
        sensor_outdoor_temp = self.hass.states.get(self.sensor_outdoor_temp)
        sensor_outdoor_humidity = self.hass.states.get(self.sensor_outdoor_humidity)

        if None in (sensor_indoor_temp, sensor_indoor_humidity, sensor_outdoor_temp, sensor_outdoor_humidity):
            raise ValueError("One or more sensors are unavailable")

        if sensor_indoor_temp.state == STATE_UNKNOWN or sensor_indoor_humidity.state == STATE_UNKNOWN or sensor_outdoor_temp.state == STATE_UNKNOWN or sensor_outdoor_humidity.state == STATE_UNKNOWN:
            raise ValueError("One or more sensors have an unknown state")

        try:
            self.indoor_temp = float(sensor_indoor_temp.state)
            self.indoor_humidity = float(sensor_indoor_humidity.state)
            self.outdoor_temp = float(sensor_outdoor_temp.state)
            self.outdoor_humidity = float(sensor_outdoor_humidity.state)
            self.add_sample((self.indoor_temp, self.indoor_humidity, self.outdoor_temp, self.outdoor_humidity))
        except ValueError:
            raise ValueError("Unable to update sensor data")

    def add_sample(self, value):
        """Add given sensor data sample to sample shift register."""
        self.samples.append(value)

    def calculate_dew_point(self, temperature, humidity):
        """Calculate the dew point temperature."""
        a = 17.27
        b = 237.7
        alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)
        return (b * alpha) / (a - alpha)

    def calc_delta(self, dew_point1, dew_point2):
        """Calculate the delta between two dew point temperatures."""
        return abs(dew_point1 - dew_point2)

    def set_on(self):
        """Turn the ventilation on."""
        if self._state == STATE_ON:
            return
        self._state = STATE_ON
        self.min_on_timer = datetime.now() + self.min_on_time
        self.max_on_timer = datetime.now() + self.max_on_time
        _LOGGER.debug("Turning on ventilation for '%s'", self.name)
        self.hass.states.set(self.low_speed, STATE_ON)
        self.hass.states.set(self.high_speed, STATE_ON)

    def set_off(self):
        """Turn the ventilation off."""
        if self._state == STATE_OFF:
            return
        self._state = STATE_OFF
        self.min_on_timer = None
        self.max_on_timer = None
        _LOGGER.debug("Turning off ventilation for '%s'", self.name)
        self.hass.states.set(self.low_speed, STATE_OFF)
        self.hass.states.set(self.high_speed, STATE_OFF)

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state of the ventilation."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "indoor_dew_point": self.indoor_dew_point,
            "outdoor_dew_point": self.outdoor_dew_point,
        }

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id
