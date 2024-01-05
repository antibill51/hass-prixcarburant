"""Tools for Prix Carburant."""
from asyncio import timeout
import json
import logging
from math import atan2, cos, radians, sin, sqrt
import os
from socket import gaierror

from aiohttp import ClientError, ClientSession

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_NAME

from .const import (
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_CITY,
    ATTR_DISTANCE,
    ATTR_FUELS,
    ATTR_POSTAL_CODE,
    ATTR_PRICE,
    ATTR_UPDATED_DATE,
    FUELS,
)

_LOGGER = logging.getLogger(__name__)

PRIX_CARBURANT_API_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records"
STATIONS_NAME_FILE = "stations_name.json"


class PrixCarburantTool:
    """Prix Carburant class with stations information."""

    def __init__(
        self,
        time_zone: str = "Europe/Paris",
        request_timeout: int = 30,
        session: ClientSession | None = None,
    ) -> None:
        """Init tool."""
        self._user_time_zone = time_zone
        self._stations_names: dict[str, dict] = {}
        self._stations_data: dict[str, dict] = {}

        _LOGGER.debug("Load stations names from local file %s", STATIONS_NAME_FILE)
        with open(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), STATIONS_NAME_FILE
            ),
            encoding="UTF-8",
        ) as file:
            self._stations_names = json.load(file)

        self._request_timeout = request_timeout
        self._session = session
        self._close_session = False

        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

    @property
    def stations(self) -> dict:
        """Return stations information."""
        return self._stations_data

    async def _request_api(
        self,
        params: dict,
    ) -> dict:
        """Make a request to the JSON API."""
        try:
            params.update(
                {
                    "lang": "fr",
                    "timezone": self._user_time_zone,
                }
            )
            async with timeout(self._request_timeout):
                response = await self._session.request(  # type: ignore[union-attr]
                    method="GET", url=PRIX_CARBURANT_API_URL, params=params
                )
                content = await response.json()

                if response.status == 200 and "results" in content:
                    response.close()
                    return content

                raise PrixCarburantToolRequestError(
                    f"API request error {response.status}: {content}"
                )

        except TimeoutError as exception:
            raise PrixCarburantToolCannotConnectError(
                "Timeout occurred while connecting to Prix Carburant API."
            ) from exception
        except (ClientError, gaierror) as exception:
            raise PrixCarburantToolCannotConnectError(
                "Error occurred while communicating with the Prix Carburant API."
            ) from exception

    async def init_stations_from_list(
        self, stations_ids: list[int], latitude: float, longitude: float
    ) -> None:
        """Get data from station list ID."""
        data = {}
        _LOGGER.debug("Call %s API to retrieve station data", PRIX_CARBURANT_API_URL)

        for station_id in stations_ids:
            _LOGGER.debug(
                "Search station ID %s",
                station_id,
            )
            response = await self._request_api(
                {
                    "select": "id,latitude,longitude,cp,adresse,ville",
                    "where": f"id={station_id}",
                    "limit": 1,
                }
            )
            if response["total_count"] != 1:
                _LOGGER.error(
                    "%s stations returned, must be 1", response["total_count"]
                )
                continue
            data.update(
                self._build_station_data(
                    response["results"][0],
                    user_latitude=latitude,
                    user_longitude=longitude,
                )
            )

        self._stations_data = data

    async def init_stations_from_location(
        self,
        latitude: float,
        longitude: float,
        distance: int,
    ) -> None:
        """Get data from near stations."""
        data = {}
        _LOGGER.debug("Call %s API to retrieve station data", PRIX_CARBURANT_API_URL)
        response_count = await self._request_api(
            {
                "select": "id",
                "where": f"distance(geom, geom'POINT({longitude} {latitude})', {distance}km)",
                "limit": 1,
            }
        )
        stations_count = response_count["total_count"]
        _LOGGER.debug("%s stations returned by the API", stations_count)

        for query_offset in range(0, stations_count, 100):
            query_limit = (
                100
                if query_offset < stations_count - 100
                else stations_count - query_offset
            )
            _LOGGER.debug(
                "Query stations from %s to %s/%s",
                query_offset,
                query_limit,
                stations_count,
            )
            async with timeout(self._request_timeout):
                response = await self._request_api(
                    {
                        "select": "id,latitude,longitude,cp,adresse,ville",
                        "where": f"distance(geom, geom'POINT({longitude} {latitude})', {distance}km)",
                        "offset": query_offset,
                        "limit": query_limit,
                    }
                )
            for station in response["results"]:
                data.update(
                    self._build_station_data(
                        station, user_longitude=longitude, user_latitude=latitude
                    )
                )

        self._stations_data = data

    async def update_stations_prices(self) -> None:
        """Update prices of specified stations."""
        _LOGGER.debug("Call %s API to retrieve fuel prices", PRIX_CARBURANT_API_URL)
        query_select = ",".join(
            [f"{f.lower()}_prix" for f in FUELS] + [f"{f.lower()}_maj" for f in FUELS]
        )
        for station_id, station_data in self._stations_data.items():
            _LOGGER.debug(
                "Update fuel prices for station id %s: %s",
                station_id,
                station_data[ATTR_NAME],
            )
            response = await self._request_api(
                {
                    "select": query_select,
                    "where": f"id={station_id}",
                    "limit": 1,
                }
            )
            if response["total_count"] != 1:
                _LOGGER.error(
                    "%s stations returned, must be 1", response["total_count"]
                )
                continue
            new_prices = response["results"][0]
            for fuel in FUELS:
                fuel_key = fuel.lower()
                if new_prices[f"{fuel_key}_prix"]:
                    station_data[ATTR_FUELS].update(
                        {
                            fuel: {
                                ATTR_UPDATED_DATE: new_prices[f"{fuel_key}_maj"],
                                ATTR_PRICE: new_prices[f"{fuel_key}_prix"],
                            }
                        }
                    )

    async def find_nearest_station(
        self, longitude: float, latitude: float, fuel: str, distance: int = 10
    ) -> dict:
        """Return stations near the location where the fuel price is the lowest."""
        data = {}
        _LOGGER.debug(
            "Call %s API to retrieve nearest stations ordered by price",
            PRIX_CARBURANT_API_URL,
        )
        response = await self._request_api(
            {
                "select": f"id,latitude,longitude,cp,adresse,ville,{fuel.lower()}_prix,{fuel.lower()}_maj",
                "where": f"distance(geom, geom'POINT({longitude} {latitude})', {distance}km)",
                "order_by": f"{fuel.lower()}_prix",
                "limit": 10,
            }
        )
        stations_count = response["total_count"]
        _LOGGER.debug("%s stations returned by the API", stations_count)

        for station in response["results"]:
            data.update(
                self._build_station_data(
                    station,
                    user_longitude=longitude,
                    user_latitude=latitude,
                    fuel_key=f"{fuel.lower()}_prix",
                )
            )
        return data

    def _build_station_data(
        self,
        station: dict,
        user_longitude: float | None = None,
        user_latitude: float | None = None,
        fuel_key: str | None = None,
    ) -> dict:
        data = {}
        try:
            latitude = float(station["latitude"]) / 100000
            longitude = float(station["longitude"]) / 100000
            distance = (
                _get_distance(longitude, latitude, user_longitude, user_latitude)
                if user_longitude and user_latitude
                else None
            )
            data.update(
                {
                    station["id"]: {
                        ATTR_LATITUDE: latitude,
                        ATTR_LONGITUDE: longitude,
                        ATTR_DISTANCE: distance,
                        ATTR_ADDRESS: station["adresse"],
                        ATTR_POSTAL_CODE: station["cp"],
                        ATTR_CITY: station["ville"],
                        ATTR_NAME: "undefined",
                        ATTR_BRAND: None,
                        ATTR_FUELS: {},
                    }
                }
            )
            # add fuel price if fuel key specified
            if fuel_key:
                data[station["id"]][ATTR_PRICE] = station[fuel_key]
            # add station name if existing in local data
            if str(station["id"]) in self._stations_names:
                data[station["id"]][ATTR_NAME] = (
                    str(self._stations_names[str(station["id"])]["Nom"])
                    .title()
                    .replace("Station ", "")
                )
                data[station["id"]][ATTR_BRAND] = str(
                    self._stations_names[str(station["id"])]["Marque"]
                ).title()
        except (KeyError, TypeError) as error:
            _LOGGER.error(
                "Error while getting station %s information: %s",
                station.get("id", "no ID"),
                error,
            )
        return data


def _get_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Get distance from 2 locations."""
    earth_radius = 6371

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    calcul_a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    calcul_c = 2 * atan2(sqrt(calcul_a), sqrt(1 - calcul_a))
    return round(calcul_c * earth_radius, 2)


class PrixCarburantToolCannotConnectError(Exception):
    """Exception to indicate an error in connection."""


class PrixCarburantToolRequestError(Exception):
    """Exception to indicate an error with an API request."""
