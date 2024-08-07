import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_SENSOR_INDOOR_TEMP, CONF_SENSOR_INDOOR_HUMIDITY, CONF_SENSOR_OUTDOOR_TEMP, CONF_SENSOR_OUTDOOR_HUMIDITY, CONF_LOW_SPEED, CONF_HIGH_SPEED, CONF_DELTA_TRIGGER, CONF_TARGET_OFFSET, CONF_MIN_ON_TIME, CONF_MAX_ON_TIME, CONF_SAMPLE_INTERVAL, CONF_MIN_HUMIDITY, CONF_UNIQUE_ID

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
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
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the WMC component."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config[DOMAIN], ["wmc"])
    )

    return True
