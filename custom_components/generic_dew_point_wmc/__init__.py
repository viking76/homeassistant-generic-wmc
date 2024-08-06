"""The generic_dew_point_wmc component."""

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.device import (
    async_remove_stale_devices_links_keep_entity_device,
)
from homeassistant.helpers.typing import ConfigType

DOMAIN = "generic_dew_point_wmc"

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

DEFAULT_TOLERANCE = 3
DEFAULT_NAME = "Generic Dew Point WMC"

WMC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR_INDOOR_TEMP): cv.entity_id,
        vol.Required(CONF_SENSOR_INDOOR_HUMIDITY): cv.entity_id,
        vol.Required(CONF_SENSOR_OUTDOOR_TEMP): cv.entity_id,
        vol.Required(CONF_SENSOR_OUTDOOR_HUMIDITY): cv.entity_id,
        vol.Required(CONF_LOW_SPEED): cv.entity_id,
        vol.Required(CONF_HIGH_SPEED): cv.entity_id,
        vol.Optional(CONF_DELTA_TRIGGER, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_TARGET_OFFSET, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_MIN_ON_TIME): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_MAX_ON_TIME): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_SAMPLE_INTERVAL): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [WMC_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Generic Dew Point WMC component."""
    if DOMAIN not in config:
        return True

    for wmc_conf in config[DOMAIN]:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, Platform.CLIMATE, DOMAIN, wmc_conf, config
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    async_remove_stale_devices_links_keep_entity_device(
        hass,
        entry.entry_id,
        entry.options[CONF_SENSOR_INDOOR_TEMP],
    )

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.CLIMATE,))
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, (Platform.CLIMATE,)
    )

