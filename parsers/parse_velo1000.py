import bs4
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from sqlalchemy.orm import Session
import time
from typing import Optional

from db.models import Product
from config import BASE_URL, CATALOG_PREFIX


class Coordinator:
    def __init__(self, driver: WebDriver, db_session: Session) -> None:
        self.driver = driver
        self.category_parser = CategoryParser(driver)
        self.db_session = db_session

    def process_all_categories(self) -> None:
        self.driver.get(BASE_URL+CATALOG_PREFIX)
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
            WebDriverWait(self.driver, timeout=3).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "catalog__block"))
            )

            categories = {}
            for block in BeautifulSoup(self.driver.page_source, 'lxml').select('.catalog__block'):
                if category_label_tag := block.select_one('.catalog__label'):
                    category_name = category_label_tag.get_text(strip=True)
                else:
                    continue
                if category_link := block['href']:
                    categories[category_name] = category_link
                else:
                    continue

            print(f'({time.strftime("%H:%M:%S")}) Found {len(categories)} categories.')
            return categories
        except Exception as e:
            print(f'({time.strftime("%H:%M:%S")}) Error loading category list: {e}')
            return {}

    def _process_single_category(self, category_name: str, category_url: str) -> None:
        self.category_parser.open_category_page(category_name, BASE_URL+category_url)

        if self.category_parser.pagination_exists():
            self.category_parser.expand_category()

        products_data = self.category_parser.parse_category(category_name)
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
        number_of_products = len(self.db_session.new)
        self.db_session.commit()
        print(f'({time.strftime("%H:%M:%S")}) {number_of_products} items added to database in category {category_name}')


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
            print(f'({time.strftime("%H:%M:%S")}) Pagination not detected')
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


    def parse_category(self, name: str) -> list[dict]:
        print(f'({time.strftime("%H:%M:%S")}) Parsing category {name}...')
        try:
            print(f'({time.strftime("%H:%M:%S")}) Start loading products')
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "product__block"))
            )
            page_html = self.driver.page_source
            return self._process_products(page_html)
        except TimeoutException:
            print(f"({time.strftime("%H:%M:%S")}) Timeout loading products in {name}")
            return []

    def _process_products(self, page_html: str) -> list[dict]:
        soup = BeautifulSoup(page_html, 'lxml')
        products = soup.select('.product__block')
        result = []
        for product_block in products:
            if product_data_dict := self.product_parser.parse_product(product_block):
                result.append(product_data_dict)
        return result


class ProductParser:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    @staticmethod
    def _extract_product_name(product_block: bs4.Tag) -> str:
        if product_label := product_block.select_one('.product__label'):
            return product_label.get_text(strip=True)
        print(f"({time.strftime("%H:%M:%S")}) Product name element not found")
        return ""

    def _extract_product_price(self, product_block: bs4.Tag) -> Optional[int]:
        if product_price := product_block.select_one('.product__price'):
            for child in product_price.children:
                if child.name == 'div' and 'line-through' not in child.get('style', ''):
                    return self._text_price_to_kopecks(child.get_text(strip=True))
            if price_text := product_price.get_text(strip=True):
                return self._text_price_to_kopecks(price_text)
        print(f"({time.strftime("%H:%M:%S")}) Product price element not found")
        return None

    @staticmethod
    def _text_price_to_kopecks(price_text: str) -> Optional[int]:
        if digits := ''.join(symbol for symbol in price_text if symbol.isdigit()):
            try:
                price_kopecks = int(digits) * 100
                return price_kopecks
            except ValueError as e:
                print(f'({time.strftime("%H:%M:%S")}) Error converting price {price_text}: {e}')
                return None
        return None

    def parse_product(self, product_block: bs4.Tag) -> Optional[dict]:
        product_data_dict = {}
        try:
            product_data_dict["name"] = self._extract_product_name(product_block)
            if not product_data_dict["name"]:
                return None
            product_data_dict["price"] = self._extract_product_price(product_block)
            return product_data_dict
        except Exception as e:
            print(f"({time.strftime("%H:%M:%S")}) Failed to parse product: {str(e)}")
            return {}

