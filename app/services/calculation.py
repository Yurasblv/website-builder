from decimal import Decimal

from app.core import settings
from app.core.exc import NotEnoughBalanceForGeneration


class CalculationService:
    @staticmethod
    def cluster_pages_generation(pages_number: int) -> Decimal:
        return round(pages_number * settings.PAGE_PRICE, 2)

    @staticmethod
    async def user_has_enough_balance(balance: Decimal, topics_number: int) -> None:
        total_price = round(topics_number * settings.PAGE_PRICE, 2)

        if balance < total_price:
            raise NotEnoughBalanceForGeneration("Not enough balance to continue.")
