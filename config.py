from selenium.webdriver.chrome.options import Options

URL = "https://velo1000.ru/catalog/"

def configure_chrome_options() -> Options:
    options = Options()
    options.add_argument("--incognito")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = 'eager'
    return options