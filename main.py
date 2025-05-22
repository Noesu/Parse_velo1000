from selenium import webdriver
import time

from config import configure_chrome_options
from utils import init_db
from parsers import Coordinator

def main() -> None:
    print(f'({time.strftime("%H:%M:%S")}) Program started!')
    chrome_options = configure_chrome_options()
    session_factory = init_db()

    with webdriver.Chrome(options=chrome_options) as driver:
        with session_factory() as session:
            coordinator = Coordinator(driver, session)
            coordinator.process_all_categories()


if __name__ == "__main__":
    main()
