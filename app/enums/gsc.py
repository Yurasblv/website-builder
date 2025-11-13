from app.enums.base import BaseStrEnum


class Xpath(BaseStrEnum):
    LOGIN_CONTINUE_BUTTON = '//*[@id="yDmH0d"]/c-wiz/div/div/div[2]/div[1]/div[2]/div/div[2]/div[2]/div/a/span/span'

    DOMAIN_FIELD = '//input[@aria-label="example.com"]'
    DNS_CONTINUE_BUTTON = '(//span[@class="RveJvd snByac"])'
    DNS_ADDITIONAL_DOMAIN_CONTINUE_BUTTON = '(//span[@class="RveJvd snByac"])[3]'
    DNS_VERIFICATION_CODE_FIELD = "//textarea"
    DOMAIN_RESOURCES_DROPDOWN = '(//input[@class="whsOnd zHQkBf"])[2]'
    DOMAIN_ADD_RESOURCE_BUTTON = '//div[@class="KUiJOe"]//div'
    DOMAIN_CONFIRM_BUTTON = (
        '(//div[@class="U26fgb O0WRkf oG5Srb C0oVfc kHssdc zkRr9b M9Bg4d"]'
        '//span[@class="CwaK9"]//span[@class="RveJvd snByac"])[2]'
    )
    DOMAIN_CONFIRM_HEADER = '//div[@class="R6Lfte tOrNgd qRUolc"]'
    DOMAIN_OK_BUTTON = (
        '(//div[@class="U26fgb O0WRkf oG5Srb HQ8yf C0oVfc kHssdc HvOprf cBsPk M9Bg4d"]'
        '//span[@class="CwaK9"]//span[@class="RveJvd snByac"])[2]'
    )
    DOMAIN_EXIT_BUTTON = (
        '(//div[@class="U26fgb O0WRkf oG5Srb HQ8yf C0oVfc kHssdc HvOprf M9Bg4d"]'
        '//span[@class="CwaK9"]//span[@class="RveJvd snByac"])[2]'
    )

    SITEMAP_BUTTON = (
        '//div[@class="cp8g2d" and @jsname="tY7zpf"]//a[@class="Lhhaec"]//span[@class="QPTmJc"]//span[@class="SaG06d"]'
    )
    SITEMAP_INPUT = (
        "/html/body/div[8]/c-wiz[2]/div/div[2]/div/div/c-wiz[1]/div/span/div[2]/div[1]/div/div/div[1]/div/div[1]/input"
    )
    SITEMAP_SEND_BUTTON = (
        '//div[@role="button" and @class="U26fgb O0WRkf zZhnYe e3Duub'
        ' C0oVfc zaJEjb M9Bg4d"]//span[@class="CwaK9"]'
        '//span[@class="RveJvd snByac"]'
    )
    DISABLE_GEOLOCATION_POP_UP = '//div[@class="mpQYc"]//div[@class="lv7K9c"]//div[@class="sjVJQd"]'
    SEARCH_URLS = '//a[contains(@class, "zReHs") and @jsname="UWckNb"]'


class Styles(BaseStrEnum):
    BACKGROUND_COLOR_RED = "rgba(219, 68, 55, 1)"
