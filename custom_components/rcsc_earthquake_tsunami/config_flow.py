"""Config flow for RCSC Earthquake & Tsunami integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_SCALE, CONF_MAGNITUDE, CONF_NOTIFY_RADIUS_KM, CONF_CONSENT

def validate_scale(value: str) -> str:
    """Validate the scale input."""
    try:
        # Check format: digit followed by optional + or -
        if not value or len(value) > 2:
            raise ValueError("Invalid scale format")
        base = int(value[0])
        if not 1 <= base <= 7:
            raise ValueError("Scale must be between 1 and 7")
        if len(value) == 2 and value[1] not in ("+", "-"):
            raise ValueError("Scale can only end with + or -")
        return value
    except ValueError as err:
        raise vol.Invalid("Invalid scale value. Must be a number 1-7 with optional + or - (e.g., 5, 5+, 5-)") from err

def validate_magnitude(value: str) -> float:
    """Validate the magnitude input."""
    try:
        magnitude = float(value)
        if not 0 <= magnitude <= 10:
            raise ValueError("Magnitude must be between 0 and 10")
        return magnitude
    except ValueError as err:
        raise vol.Invalid("Invalid magnitude value. Must be a number between 0 and 10.") from err

def validate_radius(value: str) -> float:
    """Validate the notify radius input."""
    try:
        radius = float(value)
        if radius < 0:
            raise ValueError("Radius cannot be negative")
        return radius
    except ValueError as err:
        raise vol.Invalid("Invalid radius value. Must be a positive number.") from err

class RcscEarthquakeTsunamiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RCSC Earthquake & Tsunami integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_CONSENT):
                errors["base"] = "consent_required"
            # Validate the input - ensure only scale or magnitude is provided, not both
            elif user_input.get(CONF_SCALE) and user_input.get(CONF_MAGNITUDE):
                errors["base"] = "only_one_threshold"
            elif not user_input.get(CONF_SCALE) and not user_input.get(CONF_MAGNITUDE):
                errors["base"] = "threshold_required"
            else:
                try:
                    validated_input = {}
                    if CONF_SCALE in user_input:
                        validated_input[CONF_SCALE] = validate_scale(user_input[CONF_SCALE])
                    if CONF_MAGNITUDE in user_input:
                        validated_input[CONF_MAGNITUDE] = validate_magnitude(user_input[CONF_MAGNITUDE])
                    if CONF_NOTIFY_RADIUS_KM in user_input and user_input[CONF_NOTIFY_RADIUS_KM]:
                        validated_input[CONF_NOTIFY_RADIUS_KM] = validate_radius(user_input[CONF_NOTIFY_RADIUS_KM])

                    return self.async_create_entry(
                        title="RCSC Earthquake & Tsunami",
                        data=validated_input,
                    )
                except vol.Invalid as err:
                    errors["base"] = str(err)

        schema = {
            vol.Exclusive(CONF_SCALE, "threshold"): str,
            vol.Exclusive(CONF_MAGNITUDE, "threshold"): str,
            vol.Optional(CONF_NOTIFY_RADIUS_KM): str,
            vol.Required(CONF_CONSENT, default=False): bool,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
