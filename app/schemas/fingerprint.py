from pydantic import BaseModel, Field, field_validator


class FingerprintRequest(BaseModel):
    value: str = Field(..., title="User's system fingerprint")

    @field_validator("value")
    @classmethod
    def validate_fingerprint(cls, v: str) -> str:
        from app.utils.crypt import decrypt

        try:
            value = decrypt(v)
            assert value.startswith("nda")
            return value

        except Exception:
            raise ValueError("Invalid fingerprint value")
