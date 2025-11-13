from pydantic import BaseModel, Field, field_validator

from app.enums.base import Language
from app.utils import uppercase_first_letter
from app.utils.banwords import remove_banwords


class CTASection(BaseModel):
    headline: str = Field(..., examples=["Discover car tires - an essential choice for your safety"])
    paragraph: str = Field(
        ...,
        examples=[
            "Car tires are more than just rubber—they're your vehicle's connection to the road. "
            "Whether you're navigating wet, icy conditions or cruising on a highway, "
            "the right tires make all the difference"
        ],
    )

    def __bool__(self) -> bool:
        return all([self.headline, self.paragraph])

    def get_normalized(self, language: Language) -> "CTASection":
        return self.copy(
            update={
                "headline": remove_banwords(self.headline, language=language),
                "paragraph": remove_banwords(self.paragraph, language=language),
            }
        )


class Feature(BaseModel):
    title: str = Field(..., examples=["Your safety, our priority"])
    description: str = Field(
        ...,
        examples=[
            "We ensure the highest safety standards with tires you can trust for any journey, "
            "giving you peace of mind whether you're driving through busy city streets or challenging road conditions"
        ],
    )


class FeaturesSection(BaseModel):
    header: str = Field(..., examples=["Why choose premium tires?"])
    paragraph: str = Field(
        ...,
        examples=[
            "We strive to provide tires that deliver the perfect balance of safety, performance, and efficiency. "
            "Whether you're navigating city streets, highways, or wintery terrains, "
            "our products are designed to meet your needs with confidence."
        ],
    )
    features: list[Feature] = Field(..., min_length=3, max_length=3, description="List of features as dicts")

    def get_normalized(self, language: Language) -> "FeaturesSection":
        cleaned_features = [
            Feature(
                title=remove_banwords(f.title, language=language),
                description=remove_banwords(f.description, language=language),
            )
            for f in self.features
        ]

        return self.copy(
            update={
                "header": remove_banwords(self.header, language=language),
                "paragraph": remove_banwords(self.paragraph, language=language),
                "features": cleaned_features,
            }
        )


class Benefit(BaseModel):
    title: str = Field(..., examples=["Innovative technology"])
    description: str = Field(
        ...,
        examples=["Our tires are crafted using advanced materials and technologies to ensure maximum safety"],
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return uppercase_first_letter(value)


class BenefitsGrid(BaseModel):
    header: str = Field(..., examples=["Our advantages", "Nos avantages"])
    benefits: list[Benefit] = Field(..., max_length=3, description="List of benefits as dicts")

    def __bool__(self) -> bool:
        return all([self.header, self.benefits])

    def get_normalized(self, language: Language) -> "BenefitsGrid":
        cleaned_benefits = [
            Benefit(
                title=remove_banwords(benefit.title, language=language),
                description=remove_banwords(benefit.description, language=language),
            )
            for benefit in self.benefits
        ]

        return self.copy(
            update={"header": remove_banwords(self.header, language=language), "benefits": cleaned_benefits}
        )


class Card(BaseModel):
    title: str = Field(
        ...,
        examples=["Your safety, our priority"],
    )
    description: str = Field(
        ...,
        examples=["We ensure the highest safety standards with tires you can trust for any journey"],
    )

    def __bool__(self) -> bool:
        return all([self.title, self.description])

    def get_normalized(self, language: Language) -> "Card":
        return self.copy(
            update={
                "title": remove_banwords(self.title, language=language),
                "description": remove_banwords(self.description, language=language),
            }
        )
