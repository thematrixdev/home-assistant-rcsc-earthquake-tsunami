"""Constants for the RCSC Earthquake & Tsunami integration."""

DOMAIN = "rcsc_earthquake_tsunami"

CONF_SCALE = "scale"
CONF_MAGNITUDE = "magnitude"
CONF_NOTIFY_RADIUS_KM = "notify_radius_km"
CONF_CONSENT = "Please note: This is not an Earthquake Early Warning system. There will be delays in notifications."

EARTHQUAKE_SENSOR = "earthquake"
TSUNAMI_SENSOR = "tsunami"

QUAKE_URL = "http://support.rcsc.co.jp/list/quake.json"
TSUNAMI_URL = "http://support.rcsc.co.jp/list/tsunami_only.json"
