import binascii
import io
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from PIL import Image
from sentry_sdk import capture_exception
from unidecode import unidecode


def convert_python_dict(data: Any) -> Any:
    """
    Get data and recursively convert it to a dictionary that can be stored in the database.

    Args:
        data: Python dictionary

    Returns:
        Dictionary that can be stored in a database
    """

    match data:
        case list():
            return [convert_python_dict(item) for item in data]

        case dict():
            return {key: convert_python_dict(value) for key, value in data.items()}

        case datetime():
            return data.isoformat()

        case _:
            return str(data)


def text_normalize(text: str) -> str:
    decoded_keyword = unidecode(text)

    # replace quotes with spaces
    decoded_keyword = decoded_keyword.replace('"', " ")
    decoded_keyword = decoded_keyword.replace("'", " ")

    decoded_keyword = "".join([ch if ch.isalnum() or ch in [" ", "_"] else " " for ch in decoded_keyword])
    return "-".join(decoded_keyword.split()).lower()


def uppercase_first_letter(text: str) -> str:
    """
    Convert first letter of text to uppercase.

    Args:
        text: string to convert

    Returns:
        String with first letter in uppercase
    """
    if not text:
        return text

    if text[0].isupper():
        return text

    return text[0].upper() + text[1:]


def remove_quotes(text: str) -> str:
    """
    Remove quotes from text if first and last characters are quotes.

    Args:
        text: string to remove quotes

    Returns:
        String without quotes
    """

    if not text:
        return text

    if text[0] == text[-1] and text[0] in ['"', "'", "“", "”"]:
        return text[1:-1]

    return text


def capitalize_text_nodes(data: dict) -> dict:
    if isinstance(data, dict):
        return {uppercase_first_letter(key): capitalize_text_nodes(value) for key, value in data.items()}

    return data


def check_lowercase(text: str) -> bool:
    return text.strip()[0].islower()


def remove_links(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        a.unwrap()
    return str(soup)


def strip_braces(s: str) -> str:
    return s.replace("{", "").replace("}", "")


def webp_converter(data: bytes) -> bytes:
    """
    Convert image data bytes to webp.

    Args:
        data: bytes of image file

    Returns:
        bytes transformed to webp extension
    """
    from app.core.exc import BadRequestException

    try:
        with Image.open(io.BytesIO(data)) as f:
            webp_output = io.BytesIO()
            f.save(webp_output, format="WEBP")
            data = webp_output.getvalue()
            webp_output.close()

    except binascii.Error:
        raise BadRequestException("Cannot decode provided base64 image")

    except Exception as e:
        capture_exception(e)
        raise BadRequestException(f"Error while converting avatar: {e}")

    return data
