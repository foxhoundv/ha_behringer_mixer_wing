"""Constants for Behringer Wing Mixer integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Behringer Wing Mixer"
DOMAIN = "ha_behringer_mixer_wing"
VERSION = "0.1.1"
ATTRIBUTION = ""
MIXER_TYPES = ["WING"]  # Remove X32, M32, XR18, etc.
