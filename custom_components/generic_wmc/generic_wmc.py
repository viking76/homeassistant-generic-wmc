"""
Adds support for generic dew point WMC units.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.generic_wmc/
"""
import asyncio
import collections
from datetime import timedelta, datetime
import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNKNOWN, CONF_NAME, CONF_UNIQUE_ID
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["sensor"]

SAMPLE_DURATION = timedelta(minutes=15)

DEFAULT_NAME = "Generic Dew Point WMC"

ATTR_NUMBER_OF_SAMPLES = "number_of_samples"
ATTR_LOWEST_SAMPLE = "lowest_sample"
ATTR_TARGET = "target"
ATTR_MIN_ON_TIMER = "min_on_timer"
ATTR_MAX_ON_TIMER = "max_on_timer"
ATTR_MIN_HUMIDITY = "min_humidity"
ATTR_DEW_POINT = "dew_point"

CONF_SENSOR_INDOOR_TEMP = "sensor_indoor_temp"
CONF_SENSOR_INDOOR_HUMIDITY = "sensor_indoor_humidity"
CONF_SENSOR_OUTDOOR_TEMP = "sensor_outdoor_temp"
CONF_SENSOR_OUTDOOR_HUMIDITY = "sensor_outdoor_humidity"
CONF_DELTA_TRIGGER = "delta_trigger"
CONF_TARGET_OFFSET = "target_offset"
CONF_MIN_ON_TIME = "min_on_time"
CONF_MAX_ON_TIME = "max_on_time"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_SAMPLE_INTERVAL = "sample_interval"
CONF_LOW_SPEED = "low_speed"
CONF_HIGH_SPEED = "high_speed"

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
        vol.Required(CONF_LOW_SPEED): cv.entity_id,  # Vitesse basse
        vol.Required(CONF_HIGH_SPEED): cv.entity_id,  # Vitesse haute
        vol.Optional(CONF_DELTA_TRIGGER, default=DEFAULT_DELTA_TRIGGER): vol.Coerce(float),
        vol.Optional(CONF_TARGET_OFFSET, default=DEFAULT_TARGET_OFFSET): vol.Coerce(float),
        vol.Optional(CONF_MIN_ON_TIME, default=DEFAULT_MIN_ON_TIME): cv.time_period,
        vol.Optional(CONF_MAX_ON_TIME, default=DEFAULT_MAX_ON_TIME): cv.time_period,
        vol.Optional(CONF_SAMPLE_INTERVAL, default=DEFAULT_SAMPLE_INTERVAL): cv.time_period,
        vol.Optional(CONF_MIN_HUMIDITY, default=DEFAULT_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Generic Dew Point Hygrostat platform."""
    name = config.get(CONF_NAME)
    sensor_indoor_temp = config.get(CONF_SENSOR_INDOOR_TEMP)
    sensor_indoor_humidity = config.get(CONF_SENSOR_INDOOR_HUMIDITY)
    sensor_outdoor_temp = config.get(CONF_SENSOR_OUTDOOR_TEMP)
    sensor_outdoor_humidity = config.get(CONF_SENSOR_OUTDOOR_HUMIDITY)
    delta_trigger = config.get(CONF_DELTA_TRIGGER)
    target_offset = config.get(CONF_TARGET_OFFSET)
    min_on_time = config.get(CONF_MIN_ON_TIME)
    max_on_time = config.get(CONF_MAX_ON_TIME)
    sample_interval = config.get(CONF_SAMPLE_INTERVAL)
    min_humidity = config.get(CONF_MIN_HUMIDITY)
    unique_id = config.get(CONF_UNIQUE_ID)

    async_add_devices(
        [
            GenericDewPointHygrostat(
                hass,
                name,
                sensor_indoor_temp,
                sensor_indoor_humidity,
                sensor_outdoor_temp,
                sensor_outdoor_humidity,
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


class GenericDewPointHygrostat(Entity):
    """Representation of a Generic Dew Point Hygrostat device."""

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
        """Initialize the hygrostat."""
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
        self.current_speed = None  # Ajouter un état pour la vitesse actuelle

        sample_size = int(SAMPLE_DURATION / sample_interval)
        self.samples = collections.deque([], sample_size)
        self.min_on_timer = None
        self.max_on_timer = None

        self._state = STATE_OFF
        self._icon = "mdi:water-percent"

        self._async_update()

        async_track_time_interval(hass, self._async_update, sample_interval)
        
    def set_low_speed(self):
        """Activate low speed ventilation."""
        self.hass.services.call("homeassistant", "turn_on", {"entity_id": self.low_speed})
        self.hass.services.call("homeassistant", "turn_off", {"entity_id": self.high_speed})
        self.current_speed = "low"
        self.set_state(STATE_ON)
        self.set_dehumidification_target()
        self.set_min_on_timer()
        self.set_max_on_timer()

    def set_high_speed(self):
        """Activate high speed ventilation."""
        self.hass.services.call("homeassistant", "turn_on", {"entity_id": self.high_speed})
        self.hass.services.call("homeassistant", "turn_off", {"entity_id": self.low_speed})
        self.current_speed = "high"
        self.set_state(STATE_ON)
        self.set_dehumidification_target()
        self.set_min_on_timer()
        self.set_max_on_timer()

    def set_off(self):
        """Turn off ventilation."""
        self.hass.services.call("homeassistant", "turn_off", {"entity_id": self.low_speed})
        self.hass.services.call("homeassistant", "turn_off", {"entity_id": self.high_speed})
        self.current_speed = None
        self.set_state(STATE_OFF)
        self.reset_dehumidification_target()
        self.reset_min_on_timer()
        self.reset_max_on_timer()

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

    indoor_dew_point = self.calculate_dew_point(self.indoor_temp, self.indoor_humidity)
    outdoor_dew_point = self.calculate_dew_point(self.outdoor_temp, self.outdoor_humidity)
    
    if self.target and indoor_dew_point <= self.target:
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

    dew_point_delta = self.calc_delta(indoor_dew_point, outdoor_dew_point)

    if dew_point_delta >= self.delta_trigger:
        _LOGGER.debug("High humidity detected at '%s' with delta '%s'", self.name, dew_point_delta)
        if self.current_speed != "high":
            self.set_high_speed()
    elif dew_point_delta >= self.delta_trigger / 2:
        _LOGGER.debug("Moderate humidity detected at '%s' with delta '%s'", self.name, dew_point_delta)
        if self.current_speed != "low":
            self.set_low_speed()
    else:
        _LOGGER.debug("Low humidity detected at '%s' with delta '%s'", self.name, dew_point_delta)
        self.set_off()

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

    def calc_delta(self, indoor_dew_point, outdoor_dew_point):
        """Calculate the dew point delta."""
        return indoor_dew_point - outdoor_dew_point

    def calculate_dew_point(self, temperature, humidity):
        """Calculate the dew point from temperature and humidity."""
        a = 17.27
        b = 237.7
        alpha = ((a * temperature) / (b + temperature)) + math.log(humidity/100.0)
        dew_point = (b * alpha) / (a - alpha)
        return dew_point
        
    def dew_point_to_humidity(self, temperature, dew_point):
        """Convert dew point to relative humidity for a given temperature."""
        a, b = 17.27, 237.7
        alpha = lambda temp: (a * temp) / (b + temp)
    
        alpha_t = alpha(temperature)
        alpha_dp = alpha(dew_point)
    
        humidity = (math.exp(alpha_dp - alpha_t) * 100.0)
        return humidity

    def set_dehumidification_target(self):
        """Setting dehumidification target to indoor humidity corresponding to outdoor dew point + offset."""
        # Calculer le point de rosée extérieur à partir de la température et de l'humidité extérieures
        outdoor_dew_point = self.calculate_dew_point(self.outdoor_temp, self.outdoor_humidity)
        # Vérifier que le point de rosée extérieur est calculé et que la cible n'est pas déjà définie
        if outdoor_dew_point and self.target is None:
            # Convertir le point de rosée extérieur + décalage en humidité relative intérieure cible
            indoor_humidity_target = self.dew_point_to_humidity(self.indoor_temp, outdoor_dew_point + self.target_offset)
        # Comparer l'humidité relative cible avec l'humidité minimale et définir la cible en conséquence
            if indoor_humidity_target < self.min_humidity:
                self.target = self.min_humidity
            else:
                self.target = indoor_humidity_target

    def reset_dehumidification_target(self):
        """Unsetting dehumidification target."""
        self.target = None

    def set_state(self, state):
        """Setting hygrostat sensor to given state."""
        if self._state is not state:
            self._state = state
            self.schedule_update_ha_state()

    def set_min_on_timer(self):
        """Setting min on timer."""
        if self.min_on_timer is None:
            self.min_on_timer = datetime.now() + self.min_on_time

    def reset_min_on_timer(self):
        """Unsetting min on timer."""
        self.min_on_timer = None

    def set_max_on_timer(self):
        """Setting max on timer."""
        if self.max_on_timer is None:
            self.max_on_timer = datetime.now() + self.max_on_time

    def reset_max_on_timer(self):
        """Unsetting max on timer."""
        self.max_on_timer = None

    def set_on(self):
        """Setting hygrostat to on."""
        self.set_state(STATE_ON)
        self.set_dehumidification_target()
        self.set_min_on_timer()
        self.set_max_on_timer()

    def set_off(self):
        """Setting hygrostat to off."""
        self.set_state(STATE_OFF)
        self.reset_dehumidification_target()
        self.reset_min_on_timer()
        self.reset_max_on_timer()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def state_attributes(self):
        """Return the attributes of the entity."""
        return {
            ATTR_NUMBER_OF_SAMPLES: len(self.samples),
            ATTR_LOWEST_SAMPLE: self.get_lowest_sample(),
            ATTR_TARGET: self.target,
            ATTR_MIN_ON_TIMER: self.min_on_timer,
            ATTR_MAX_ON_TIMER: self.max_on_timer,
            ATTR_MIN_HUMIDITY: self.min_humidity,
            ATTR_DEW_POINT: self.calculate_dew_point(self.indoor_temp, self.indoor_humidity) if self.indoor_temp and self.indoor_humidity else None,
        }

    @property
    def unique_id(self):
        """Return the unique id of this hygrostat."""
        return self._unique_id
