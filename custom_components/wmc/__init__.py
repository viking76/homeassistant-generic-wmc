"""The wmc component."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.device import async_remove_stale_devices_links_keep_entity_device
from homeassistant.helpers.typing import ConfigType

DOMAIN = "wmc"

# Define the schema for the configuration
WMC_SCHEMA = vol.Schema({
    vol.Required("name"): cv.string,
    vol.Required("sensor_indoor_temp"): cv.entity_id,
    vol.Required("sensor_indoor_humidity"): cv.entity_id,
    vol.Required("sensor_outdoor_temp"): cv.entity_id,
    vol.Required("sensor_outdoor_humidity"): cv.entity_id,
    vol.Optional("delta_trigger", default=3): vol.Coerce(float),
    vol.Optional("target_offset", default=3): vol.Coerce(float),
    vol.Optional("min_on_time", default="00:00:00"): cv.time_period,
    vol.Optional("max_on_time", default="02:00:00"): cv.time_period,
    vol.Optional("sample_interval", default="00:05:00"): cv.time_period,
    vol.Optional("min_humidity", default=0): vol.Coerce(float),
    vol.Optional("unique_id"): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [WMC_SCHEMA]),
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the WMC component."""
    if DOMAIN not in config:
        return True

    for wmc_conf in config[DOMAIN]:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, "climate", DOMAIN, wmc_conf, config
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    async_remove_stale_devices_links_keep_entity_device(
        hass,
        entry.entry_id,
        entry.options["sensor_indoor_temp"],
    )

    await hass.config_entries.async_forward_entry_setups(entry, ("climate",))
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True

async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, ("climate",)
    )
