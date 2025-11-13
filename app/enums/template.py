from app.enums import Language
from app.enums.base import BaseStrEnum


class TemplateType(BaseStrEnum):
    FORGOT_PASSWORD = "forgot_password"
    REGISTRATION = "registration"
    WITHDRAWAL = "withdrawal"
    REFRESH_PBN = "refresh_pbn"
    RENEW_DOMAIN = "renew_domain"
    CHECK_CTR = "check_ctr"


class TemplateTitle(BaseStrEnum):
    REGISTRATION_US = "Verify your email address"
    REGISTRATION_FR = "Vérifiez votre adresse e-mail"

    FORGOT_PASSWORD_US = "Reset your password"
    FORGOT_PASSWORD_FR = "Réinitialisez votre mot de passe"

    WITHDRAWAL_US = "NDA withdraw notification"
    WITHDRAWAL_FR = "Notification de retrait NDA"

    REFRESH_PBN_US = "Refresh PBN"
    REFRESH_PBN_FR = "Rafraîchir PBN"

    RENEW_DOMAIN_US = "Renew Domain"
    RENEW_DOMAIN_FR = "Renouveler le domaine"

    CHECK_CTR_US = "Check/Verify your pattern for CTR manipulation"
    CHECK_CTR_FR = "Vérifiez votre modèle de manipulation du CTR"

    default = "Unknown template title"

    @classmethod
    def get(cls, template_type: TemplateType | str, language: Language) -> str:
        template_type = template_type.name if isinstance(template_type, TemplateType) else template_type.upper()
        name = f"{template_type}_{language.value}"
        return getattr(cls, name, cls.default).value  # type: ignore
