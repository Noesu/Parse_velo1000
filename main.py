import logging
from selenium import webdriver

from config import configure_chrome_options
from utils import init_db
from utils.logger import setup_logging
from parsers import Coordinator

def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info('Program started!')
    chrome_options = configure_chrome_options()
    session_factory = init_db()

    with webdriver.Chrome(options=chrome_options) as driver:
        with session_factory() as session:
            coordinator = Coordinator(driver, session)
            coordinator.process_all_categories()


if __name__ == "__main__":
    main()
