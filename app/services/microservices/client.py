from typing import Any

from loguru import logger

from app.enums import MicroServiceType

from .request import RequestService


class MicroservicesClient:
    def __init__(self, service_type: MicroServiceType):
        self.request_service: RequestService = RequestService(service_type)

    async def send(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Sends a request to the microservice via WebSocket.

        Args:
            method_name: The name of the method to call on the microservice.
            *args: Positional arguments to pass to the microservice method.
            **kwargs: Keyword arguments to pass to the microservice method.

        Returns:
            The response from the microservice, parsed as a dictionary.
        """

        request_data = {"action": method_name, "args": args, "kwargs": kwargs}
        response = await self.request_service.send(data=request_data)

        if response.get("status") == "error":
            logger.error(f"Microservice request failed: {response.get('message', 'Unknown error')}")

        return response.get("data", None)
