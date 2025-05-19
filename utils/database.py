from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base

def init_db(db_url='sqlite:///products.db') -> sessionmaker:
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

