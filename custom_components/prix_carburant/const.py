"""Constants for the Prix Carburant integration."""
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "prix_carburant"
PLATFORMS: Final = [Platform.SENSOR, Platform.BUTTON]

DEFAULT_NAME: Final = "Prix Carburant"
DEFAULT_MAX_KM: Final = 15
DEFAULT_SCAN_INTERVAL: Final = 4

ATTR_ADDRESS = "address"
ATTR_POSTAL_CODE = "postal_code"
ATTR_BRAND = "brand"
ATTR_CITY = "city"
ATTR_DISTANCE = "distance"
ATTR_FUELS = "fuels"
ATTR_UPDATED_DATE = "updated_date"
ATTR_DAYS_SINCE_LAST_UPDATE = "days_since_last_update"
ATTR_PRICE = "price"
CONF_MAX_KM = "max_km"
CONF_FUELS = "fuels"
CONF_STATIONS = "stations"
CONF_DISPLAY_ENTITY_PICTURES = "display_entity_pictures"

ATTR_GAZOLE = "Gazole"
ATTR_SP95 = "SP95"
ATTR_SP98 = "SP98"
ATTR_E10 = "E10"
ATTR_E85 = "E85"
ATTR_GPL = "GPLc"
FUELS = [ATTR_E10, ATTR_E85, ATTR_SP95, ATTR_SP98, ATTR_GAZOLE, ATTR_GPL]
