import asyncio
from io import BytesIO

import aiohttp
import piexif
from loguru import logger
from PIL import Image

from app.enums import ImagePrompts
from app.schemas.elements.cluster_pages.base import GeolocationSchema, UserMetadataSchema
from app.services.ai import AIBase
from app.utils.geolocation import call_nominatim_geocoder, convert_to_dms, get_exif_time


class ImageProcessor:
    """Image processor for adding geolocation and user metadata to images.

    Args:
        country: Optional country name for geolocation
        city: Optional city name for geolocation
    """

    def __init__(self, country: str | None = None, city: str | None = None) -> None:
        self.ai = AIBase()
        self.country = country
        self.city = city
        self.user_metadata = None

    async def process_image(self, image_bytes: bytes) -> bytes:
        """
        Process image from link and return as bytes with added metadata

        Args:
            image_bytes: Raw image bytes

        Returns:
            Processed image with EXIF metadata as bytes
        """

        await self.generate_user_metadata()

        geo_data = await self._get_geolocation_data()
        exif_data = self._create_exif_metadata(geo_data)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.add_exif_metadata, image_bytes, exif_data)

    @staticmethod
    async def _fetch_image_bytes(image_uri: str) -> bytes:
        """
        Fetch image data from URL

        Args:
            image_uri: URL of the image to fetch

        Returns:
            Raw image bytes
        """

        async with aiohttp.ClientSession(raise_for_status=True) as session, session.get(image_uri) as response:
            return await response.read()

    @property
    def address(self) -> str:
        """
        Return the formatted address string using city and country

        Returns:
            Formatted address string containing city and country if available,
            otherwise just country
        """

        return f"{self.city}, {self.country}" if self.city else str(self.country)

    async def _get_geolocation_data(self) -> tuple[float | None, float | None]:
        """
        Get geolocation data from settings

        Returns:
            Tuple containing latitude and longitude as floats, or None if geocoding fails
        """

        try:
            latitude, longitude = await call_nominatim_geocoder(self.address)

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            latitude, longitude = None, None

        return latitude, longitude

    def _create_exif_metadata(self, geo_data: tuple[float | None, float | None]) -> dict:
        """
        Create EXIF metadata dictionary

        Args:
            geo_data: Tuple containing latitude and longitude

        Returns:
            Dictionary containing EXIF metadata ready to be added to an image
        """

        latitude, longitude = geo_data
        exif_time = get_exif_time()

        lat_dms, lon_dms, lat_ref, lon_ref = self._process_coordinates(latitude, longitude)

        camera_brand = getattr(self.user_metadata, "camera_brand", "Sony")
        camera_model = getattr(self.user_metadata, "camera_model", "Sony Alpha 1 II")
        owner_name = getattr(self.user_metadata, "name", "John Smith")

        return {
            "0th": {
                piexif.ImageIFD.Make: camera_brand,
                piexif.ImageIFD.Model: camera_model,
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: exif_time,
                piexif.ExifIFD.CameraOwnerName: owner_name,
            },
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: lat_ref,
                piexif.GPSIFD.GPSLatitude: lat_dms,
                piexif.GPSIFD.GPSLongitudeRef: lon_ref,
                piexif.GPSIFD.GPSLongitude: lon_dms,
            },
            "1st": {},
            "thumbnail": None,
        }

    @staticmethod
    def _process_coordinates(latitude: float | None, longitude: float | None) -> tuple:
        """
        Convert decimal coordinates to DMS format with reference directions.

        Args:
            latitude: Decimal latitude value or None
            longitude: Decimal longitude value or None

        Returns:
            Tuple containing (latitude_dms, longitude_dms, latitude_ref, longitude_ref)
            or (None, None, None, None) if conversion fails
        """

        if latitude is None or longitude is None:
            return None, None, None, None

        try:
            lat_dms = convert_to_dms(latitude)
            lon_dms = convert_to_dms(longitude)
            lat_ref = "N" if latitude >= 0 else "S"
            lon_ref = "E" if longitude >= 0 else "W"
            return lat_dms, lon_dms, lat_ref, lon_ref

        except ValueError as e:
            logger.warning(f"Failed to convert coordinates to DMS: {e}")
            return None, None, None, None

    async def get_ai_geolocation(self, topic: str, country: str) -> GeolocationSchema | None:
        """
        Get country and city using GPT-4o model given topic

        Args:
            topic: Topic to determine geolocation from
            country: Default country

        Returns:
            GeolocationSchema instance with country and city information
        """

        try:
            return await self.ai.instructor_request(
                prompt=ImagePrompts.GEOLOCATION_DETECTION_PROMPT.format(topic=topic, country=country),
                output_schema=GeolocationSchema,
            )

        except Exception as e:
            logger.error(f"Error getting AI geolocation for {topic=} and {country=}: {e}")

    async def generate_user_metadata(self) -> None:
        """
        Generate user information for EXIF metadata

        Updates self.user_metadata with AI-generated user metadata or sets to None on failure

        """

        try:
            if not self.user_metadata:
                response = await self.ai.instructor_request(
                    prompt=ImagePrompts.USER_METADATA_PROMPT,
                    output_schema=UserMetadataSchema,
                    temperature=0.9,
                )
                self.user_metadata = response

        except Exception as e:
            logger.error(f"Error generating user metadata: {e}")
            self.user_metadata = None

    @staticmethod
    def add_exif_metadata(image_data: bytes, metadata: dict) -> bytes:
        """
        Add EXIF metadata to image bytes and return as bytes

        Args:
            image_data: Raw image bytes
            metadata: EXIF metadata dictionary to add to the image

        Returns:
            Modified image with EXIF metadata as bytes in WEBP format
        """

        with BytesIO(image_data) as img_bytesio, BytesIO() as img_output:
            img = Image.open(img_bytesio)
            exif_bytes = piexif.dump(metadata)

            img.save(img_output, format="WEBP", exif=exif_bytes)
            img_output.seek(0)
            return img_output.getvalue()

    @classmethod
    def read_metadata(cls, image_bytes: bytes) -> dict | None:
        """
        Read metadata from image bytes

        Args:
            image_bytes: Raw image bytes

        Returns:
            Dictionary containing EXIF metadata or None if no metadata exists
        """

        img = cls._bytes_to_image(image_bytes)
        return cls._read_exif_metadata(img)

    @staticmethod
    def _bytes_to_image(image_bytes: bytes) -> Image.Image:
        """
        Convert raw bytes to PIL Image object

        Args:
            image_bytes: Raw image bytes

        Returns:
            PIL Image object
        """

        with BytesIO(image_bytes) as img_bytesio:
            return Image.open(img_bytesio)

    @staticmethod
    def _read_exif_metadata(img: Image.Image) -> dict | None:
        """
        Read EXIF metadata from PIL Image

        Args:
            img: PIL Image object

        Returns:
            Dictionary containing EXIF metadata or None if no metadata exists
        """

        exif_data = img._getexif()
        if exif_data is None:
            return None

        return piexif.load(img.info["exif"]) if "exif" in img.info else {}
