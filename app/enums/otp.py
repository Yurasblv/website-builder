from .base import AppType, BaseStrEnum


class OTPAction(BaseStrEnum):
    REGISTRATION = "registration"
    FORGOT_PASSWORD = "forgot_password"

    @staticmethod
    def get_url(app: AppType, action: "OTPAction", code: str = None) -> str:
        from app.core import settings

        pattern = "{base_url}{suffix}"
        match app, action:
            case (AppType.DESKTOP, OTPAction.REGISTRATION):
                base_url = settings.API_URL
                suffix = f"/api/desktop?q=otp_registration%3D{code}"
            case (AppType.DESKTOP, OTPAction.FORGOT_PASSWORD):
                base_url = settings.API_URL
                suffix = f"/api/desktop?q=otp_reset_password%3D{code}"
            case (_, OTPAction.REGISTRATION):
                base_url = settings.LANDING_URL
                suffix = f"/code?otp={code}"
            case (_, OTPAction.FORGOT_PASSWORD):
                base_url = settings.LANDING_URL
                suffix = f"/reset-password?otp={code}"
            case _:
                raise ValueError(f"URL for {app} and {action} is not defined.")

        return pattern.format(base_url=base_url, suffix=suffix)
