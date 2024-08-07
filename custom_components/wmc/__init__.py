import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_PLATFORM
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
            vol.Required("platform"): cv.string,
            vol.Required("sensor_indoor_temp"): cv.entity_id,
            vol.Required("sensor_indoor_humidity"): cv.entity_id,
            vol.Required("sensor_outdoor_temp"): cv.entity_id,
            vol.Required("sensor_outdoor_humidity"): cv.entity_id,
            vol.Required("low_speed"): cv.entity_id,
            vol.Required("high_speed"): cv.entity_id,
            vol.Optional("delta_trigger", default=3): cv.positive_int,
            vol.Optional("target_offset", default=3): cv.positive_int,
            vol.Optional("min_on_time", default="00:05:00"): cv.time_period,
            vol.Optional("max_on_time", default="02:00:00"): cv.time_period,
            vol.Optional("sample_interval", default="00:05:00"): cv.time_period,
            vol.Optional("min_humidity", default=30): cv.positive_int,
            vol.Optional("unique_id"): cv.string,
        }),
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the WMC component."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config[DOMAIN], ["climate"])
    )

    return True
