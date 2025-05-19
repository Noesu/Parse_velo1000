from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Product(Base):
    __tablename__ = 'goods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(200), nullable=False)
    product_name = Column(String(200), nullable=False)
    price_kopecks = Column(Integer, nullable=True)
    parsed_at = Column(DateTime, default=datetime.now)
