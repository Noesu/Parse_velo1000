from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from sqlalchemy.orm import Session
import time
from typing import Optional

from db.models import Product


class Coordinator:
    def __init__(self, driver: WebDriver, db_session: Session) -> None:
        self.driver = driver
        self.category_parser = CategoryParser(driver)
        self.db_session = db_session

    def process_all_categories(self, url: str) -> None:
        self.driver.get(url)
        categories = self._read_categories()

        for category_name, category_url in categories.items():
            try:
                self._process_single_category(category_name, category_url)
            except Exception as e:
                self._handle_category_error(category_name, category_url, e)
                continue

    def _read_categories(self) -> dict[str, str]:
        try:
            print(f'({time.strftime("%H:%M:%S")}) Reading categories... ')
            category_list = WebDriverWait(self.driver, timeout=3).until(
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
            print(f'({time.strftime("%H:%M:%S")}) {len(categories)} categories have links. ')
            return categories
        except Exception as e:
            print(f'({time.strftime("%H:%M:%S")}) Error loading category list')
            return {}

    def _process_single_category(self, category_name: str, url: str) -> None:
        self.category_parser.open_category_page(category_name, url)

        if self.category_parser.pagination_exists():
            self.category_parser.expand_category()

        products_data = self.category_parser.parse_category(category_name, url)
        self._save_products_to_db(category_name, products_data)


    def _handle_category_error(self, name: str, url: str, error: Exception) -> None:
        error_msg = f"Error processing category '{name}' ({url}): {str(error)}"
        print(f'({time.strftime("%H:%M:%S")}) {error_msg}')
        self.db_session.rollback()

    def _save_products_to_db(self, category_name: str, products_data: list[dict]) -> None:
        for product_data in products_data:
            if not product_data.get('name') or product_data.get('price') is None:
                continue

            product = Product(
                category_name=category_name,
                product_name=product_data['name'],
                price_kopecks=product_data['price'],
            )
            self.db_session.add(product)
        self.db_session.commit()


class CategoryParser:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver
        self.product_parser = ProductParser(self.driver)

    def open_category_page(self, name: str, url: str) -> None:
        print(f'({time.strftime("%H:%M:%S")}) Opening category {name}...')
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, timeout=10).until(EC.url_to_be(url))
            print(f'({time.strftime("%H:%M:%S")}) Category {name} opened')
            WebDriverWait(self.driver, timeout=10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product__block"))
            )
        except TimeoutException:
            print(f'({time.strftime("%H:%M:%S")}) Timeout while opening page: {url}')

    def pagination_exists(self) -> bool:
        try:
            WebDriverWait(self.driver, timeout=3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pagination"))
            )
            return True

        except TimeoutException:
            print(f'Pagination not detected')
            return False

    def expand_category(self) -> None:
        print(f'({time.strftime("%H:%M:%S")}) Pagination detected. Expanding...')
        try:
            count_element = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".top__items-count[data-count='999']"))
            )
            count_element.click()
            WebDriverWait(self.driver, 15).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "pagination"))
            )
            print(f'({time.strftime("%H:%M:%S")}) Category expanded successfully.')
        except TimeoutException as e:
            print(f'({time.strftime("%H:%M:%S")}) Error during expanding category: {str(e)}')


    def parse_category(self, name: str, url: str) -> list[dict]:
        print(f'({time.strftime("%H:%M:%S")}) Parsing category {name}...')
        try:
            print(f'({time.strftime("%H:%M:%S")}) Start loading products')
            products = self.product_parser.get_products_list()
            print(f'({time.strftime("%H:%M:%S")}) Loaded {len(products)} products in category')
            return self._process_products(products)
        except TimeoutException:
            print(f"Timeout loading products in {name}")
            return []

    def _process_products(self, products: list[WebElement]) -> list[dict]:
        result = []
        for product in products:
            if product_data := self.product_parser.parse_product(product):
                result.append(product_data)
        return result


class ProductParser:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    @staticmethod
    def _extract_product_name(product: WebElement) -> str:
        try:
            return product.find_element(By.CLASS_NAME, "product__label").text
        except NoSuchElementException:
            print(f"({time.strftime("%H:%M:%S")}) Product name element not found")
            return ""
        except Exception as e:
            print(f"({time.strftime("%H:%M:%S")}) Unexpected error extracting name: {str(e)}")
            return ""

    def _extract_product_price(self, product: WebElement) -> Optional[int]:
        try:
            price_text = product.find_element(By.CLASS_NAME, "product__price").text
            return self._text_price_to_kopecks(price_text)
        except NoSuchElementException:
            print(f"({time.strftime("%H:%M:%S")}) Product price element not found")
            return None
        except Exception as e:
            print(f"({time.strftime("%H:%M:%S")}) Unexpected error extracting price: {str(e)}")
            return None

    @staticmethod
    def _text_price_to_kopecks(price_text: str) -> Optional[int]:
        try:
            digits = ''.join(symbol for symbol in price_text if symbol.isdigit())
            if not digits:
                return None
            price_kopecks = int(digits) * 100
            return price_kopecks
        except Exception as e:
            print(f'Error converting price {price_text}: {e}')
            return None


    def get_products_list(self) -> list[WebElement]:
        return WebDriverWait(self.driver, 60).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "product__block"))
        )

    def parse_product(self, product: WebElement) -> Optional[dict]:
        product_data = {}
        try:
            product_data["name"] = self._extract_product_name(product)
            if not product_data["name"]:
                return None
            product_data["price"] = self._extract_product_price(product)
            print(product_data)
            return product_data
        except Exception as e:
            print(f"Failed to parse product: {str(e)}")
            return {}

