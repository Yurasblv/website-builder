import asyncio
import datetime
import random
from concurrent.futures import ThreadPoolExecutor

from geopy.geocoders import Nominatim
from loguru import logger

_executor = ThreadPoolExecutor()


async def call_nominatim_geocoder(address: str) -> tuple[float | None, float | None]:
    """
    Get coordinates by address

    Args:
        address: The address to geocode

    Returns:
        Tuple containing latitude and longitude as floats, or (None, None) if geocoding fails

    Raises:
        Exception: If geocoding service fails
    """
    if not address:
        logger.error("No address provided")
        return None, None

    geolocator = Nominatim(user_agent="my_agent")
    loop = asyncio.get_running_loop()

    try:
        get_loc = await loop.run_in_executor(_executor, lambda: geolocator.geocode(address, timeout=10))
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        return None, None

    if get_loc:
        return get_loc.latitude, get_loc.longitude

    return None, None


def convert_to_dms(degree: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """
    Convert decimal degrees to degrees, minutes, seconds.

    Args:
        degree: Decimal degree value to convert

    Returns:
        Tuple of tuples representing degrees, minutes, seconds in the format:
        ((degrees, denominator), (minutes, denominator), (seconds, denominator))
    """
    if not (-180 <= degree <= 180):
        raise ValueError(f"Invalid degree value: {degree}. It must be between -180 and 180.")

    d = abs(degree)
    degrees = int(d)
    minutes = int((d - degrees) * 60)
    seconds = (d - degrees - minutes / 60) * 3600

    return (degrees, 1), (minutes, 1), (int(seconds * 10000), 10000)


def get_exif_time() -> str:
    """
    Get current date and time

    Returns:
        String formatted date and time that is 1-10 hours in the past,
        in the format 'YYYY:MM:DD HH:MM:SS'
    """
    random_hours = random.randint(1, 10)
    past_time = datetime.datetime.now() - datetime.timedelta(hours=random_hours)
    return past_time.strftime("%Y:%m:%d %H:%M:%S")
