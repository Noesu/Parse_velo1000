from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time

URL = "https://velo1000.ru/catalog/"


def main() -> None:
    print(f'({time.strftime("%H:%M:%S")}) Program started!')
    chrome_options = configure_chrome_options()
    with webdriver.Chrome(options=chrome_options) as driver:
        driver.get(URL)
        categories = read_categories(driver)
        print(f'({time.strftime("%H:%M:%S")}) Categories loaded from {URL}: {len(categories)}')
        for category in categories.items():
            try:
                print(f'({time.strftime("%H:%M:%S")}) Parsing category {category[0]}...')
                parse_category(driver, category)
            except Exception as e:
                print(f'({time.strftime("%H:%M:%S")}) Таймаут при обработке категории {category[0]}: {str(e)}')
                continue

def configure_chrome_options() -> Options:
    options = Options()
    options.add_argument("--incognito")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = 'eager'
    return options

def read_categories(driver: WebDriver) -> dict[str, str]:
    wait = WebDriverWait(driver, timeout=3)
    try:
        category_list = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "catalog__block"))
        )
        print(f'({time.strftime("%H:%M:%S")}) Found {len(category_list)} categories. ')
        categories = {}
        for category in category_list:
            try:
                category_link = category.get_attribute("href")
                if not category_link:
                    continue
                category_name = category.find_element(By.CLASS_NAME, "catalog__label").text.strip()
                if category_name and category_link:
                    categories[category_name] = category_link
            except Exception as e:
                error_context = {
                    'category': category,
                    'link': category_link or 'n/a',
                    'name': category_name or 'n/a',
                    'error': str(e)
                }
                print(f'({time.strftime("%H:%M:%S")}) Error parsing category {error_context}')
                continue
        return categories
    except Exception as e:
        print(f'({time.strftime("%H:%M:%S")}) Error loading category list')
        return {}


def parse_category(driver: WebDriver, category_data: tuple[str, str]) -> None:
    # Open category page
    category_name, category_url = category_data
    driver.get(category_url)
    WebDriverWait(driver, timeout=5).until(EC.url_to_be(category_url))
    print(f'({time.strftime("%H:%M:%S")}) Category {category_name} opened')

    #Check for pagination on the page
    try:
        pagination = WebDriverWait(driver, timeout=3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pagination"))
        )
        if pagination:
            print(f'({time.strftime("%H:%M:%S")}) Pagination detected. Expanding...')
            try:

                # Expand category if pagination detected
                count_element = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".top__items-count[data-count='999']"))
                )
                count_element.click()
                WebDriverWait(driver, 15).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "pagination"))
                )
                print(f'({time.strftime("%H:%M:%S")}) Category expanded successfully.')
            except TimeoutException as e:
                print(f'({time.strftime("%H:%M:%S")}) Error during expanding category: {str(e)}')
    except TimeoutException:
        print(f'Pagination not detected')

    # Read and parse products in selected category
    try:
        print(f'({time.strftime("%H:%M:%S")}) Start loading products')
        products = WebDriverWait(driver, timeout=60).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "product__block"))
        )
        print(f'({time.strftime("%H:%M:%S")}) Loaded {len(products)} products in category')
        for product in products:
            try:
                product_name = product.find_element(By.CLASS_NAME, "product__label").text
                product_price = product.find_element(By.CLASS_NAME, "product__price").text
                print(f'{product_name} - {product_price}')
            except TimeoutException as e:
                print(f'({time.strftime("%H:%M:%S")}) Error during product parse: {str(e)}')
                continue
    except TimeoutException:
        print(f"({time.strftime("%H:%M:%S")}) Error loading products on category: {category_url}")


if __name__ == "__main__":
    main()
