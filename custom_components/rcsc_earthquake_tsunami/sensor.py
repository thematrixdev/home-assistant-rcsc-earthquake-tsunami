"""Support for RCSC Earthquake & Tsunami sensors."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
from math import radians, sin, cos, sqrt, atan2
import aiohttp
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    CONF_SCALE,
    CONF_MAGNITUDE,
    CONF_NOTIFY_RADIUS_KM,
    QUAKE_URL,
    TSUNAMI_URL,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers."""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def compare_jma_scale(quake_scale: str, threshold: str) -> bool:
    """Compare JMA scale values, handling + and - signs.
    
    Returns True if quake_scale is greater than or equal to threshold.
    For example:
    "5+" > "5" > "5-"
    """
    def scale_value(scale: str) -> float:
        base = int(scale[0])
        if scale.endswith("+"):
            return base + 0.3
        elif scale.endswith("-"):
            return base - 0.3
        return float(base)
    
    try:
        return scale_value(quake_scale) >= scale_value(threshold)
    except (ValueError, AttributeError) as err:
        _LOGGER.error("Error comparing scales %s and %s: %s", quake_scale, threshold, err)
        return False

class RcscEarthquakeSensor(BinarySensorEntity):
    """Implementation of a RCSC Earthquake sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attributes = {}
        self._attr_unique_id = f"{entry.entry_id}_earthquake"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="RCSC Earthquake & Tsunami",
            manufacturer="RCSC",
        )
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._is_on = False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "RCSC Earthquake"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return self._attributes

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    QUAKE_URL,
                    headers={
                        "Cache-Control": "no-cache",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "User-Agent": "okhttp/2.7.5",
                    },
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
                    try:
                        data = json.loads(text)
                        _LOGGER.debug("Earthquake API response: %s", data)
                    except json.JSONDecodeError as err:
                        _LOGGER.error("Failed to decode earthquake JSON: %s. Response: %s", err, text)
                        self._is_on = False
                        return

                    if not data or "quakelist" not in data or not data["quakelist"]:
                        _LOGGER.debug("No earthquake data in response")
                        self._is_on = False
                        return

                    quake = data["quakelist"][0]["quake"]
                    if "info" not in quake or "JISHIN" not in quake["info"]:
                        _LOGGER.debug("No earthquake info in response")
                        self._is_on = False
                        return

                    jishin = quake["info"]["JISHIN"]
                    _LOGGER.debug("Processing earthquake: scale=%s, magnitude=%s", 
                                jishin.get("maxscale"), jishin.get("magnitude"))
                    
                    # Check if earthquake is within notify radius
                    if self._entry.data.get(CONF_NOTIFY_RADIUS_KM):
                        quake_lat = float(jishin["lat"])
                        quake_lon = float(jishin["lon"])
                        home_lat = self.hass.config.latitude
                        home_lon = self.hass.config.longitude
                        
                        distance = calculate_distance(
                            home_lat, home_lon, quake_lat, quake_lon
                        )
                        
                        _LOGGER.debug("Distance to earthquake: %.2f km (limit: %.2f km)", 
                                    distance, self._entry.data[CONF_NOTIFY_RADIUS_KM])
                        
                        if distance > self._entry.data[CONF_NOTIFY_RADIUS_KM]:
                            self._is_on = False
                            return

                    # Check either scale or magnitude threshold based on user configuration
                    if CONF_SCALE in self._entry.data:
                        threshold_met = compare_jma_scale(jishin["maxscale"], self._entry.data[CONF_SCALE])
                        _LOGGER.debug("Scale comparison: quake=%s, threshold=%s, met=%s",
                                    jishin["maxscale"], self._entry.data[CONF_SCALE], threshold_met)
                        if not threshold_met:
                            self._is_on = False
                            return
                    elif CONF_MAGNITUDE in self._entry.data:
                        threshold_met = float(jishin["magnitude"]) >= self._entry.data[CONF_MAGNITUDE]
                        _LOGGER.debug("Magnitude comparison: quake=%.1f, threshold=%.1f, met=%s",
                                    float(jishin["magnitude"]), self._entry.data[CONF_MAGNITUDE], threshold_met)
                        if not threshold_met:
                            self._is_on = False
                            return

                    # Check if earthquake is within last 30 minutes
                    # Parse date in Japan timezone but respect HA's timezone for comparison
                    try:
                        jp_tz = dt_util.get_time_zone("Asia/Tokyo")
                        if not jp_tz:
                            jp_tz = dt_util.get_time_zone("UTC")
                            _LOGGER.warning("Could not get Japan timezone, using UTC")
                        
                        occurrence_time = dt_util.parse_datetime(
                            jishin["occurrence_date"].replace("/", "-")
                        )
                        if occurrence_time:
                            occurrence_time = occurrence_time.replace(tzinfo=jp_tz)
                            time_diff = dt_util.utcnow() - occurrence_time.astimezone(dt_util.UTC)
                            _LOGGER.debug("Time since earthquake: %s", time_diff)
                            if time_diff < timedelta(minutes=30):
                                self._is_on = True
                                self._attributes = quake["info"]
                            else:
                                _LOGGER.debug("Earthquake too old")
                                self._is_on = False
                                self._attributes = {}
                        else:
                            _LOGGER.warning("Could not parse occurrence time: %s", jishin["occurrence_date"])
                            self._is_on = False
                    except Exception as err:
                        _LOGGER.error("Error processing time: %s", err)
                        self._is_on = False

        except Exception as err:
            _LOGGER.error("Error updating earthquake sensor: %s", err)
            self._is_on = False

class RcscTsunamiSensor(BinarySensorEntity):
    """Implementation of a RCSC Tsunami sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attributes = {}
        self._attr_unique_id = f"{entry.entry_id}_tsunami"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="RCSC Earthquake & Tsunami",
            manufacturer="RCSC",
        )
        self._attr_device_class = BinarySensorDeviceClass.SAFETY
        self._is_on = False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "RCSC Tsunami"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return self._attributes

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TSUNAMI_URL,
                    headers={
                        "Cache-Control": "no-cache",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "User-Agent": "okhttp/2.7.5",
                    },
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
                    try:
                        data = json.loads(text)
                        _LOGGER.debug("Tsunami API response: %s", data)
                    except json.JSONDecodeError as err:
                        _LOGGER.error("Failed to decode tsunami JSON: %s. Response: %s", err, text)
                        self._is_on = False
                        return

                    if not data or "quakelist" not in data or not data["quakelist"]:
                        _LOGGER.debug("No tsunami data in response")
                        self._is_on = False
                        return

                    quake = data["quakelist"][0]["quake"]
                    if "info" not in quake or "TUNAMI" not in quake["info"]:
                        _LOGGER.debug("No tsunami info in response")
                        self._is_on = False
                        return

                    tsunami = quake["info"]["TUNAMI"]
                    _LOGGER.debug("Processing tsunami info: %s", tsunami)

                    # Check if there are advisory locations
                    if "advisory" in tsunami:
                        self._is_on = True
                        self._attributes = {"locations": tsunami["advisory"]}
                        _LOGGER.debug("Tsunami warning active for locations: %s", tsunami["advisory"])
                    elif "none" in tsunami:
                        self._is_on = False
                        self._attributes = {}
                        _LOGGER.debug("No tsunami warnings active")
                    else:
                        _LOGGER.warning("Unexpected tsunami data format: %s", tsunami)
                        self._is_on = False
                        self._attributes = {}

        except Exception as err:
            _LOGGER.error("Error updating tsunami sensor: %s", err)
            self._is_on = False
            self._attributes = {}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the RCSC Earthquake & Tsunami sensors."""
    async_add_entities(
        [
            RcscEarthquakeSensor(hass, entry),
            RcscTsunamiSensor(hass, entry),
        ],
        True,
    )
    return True
