from sqlalchemy import Column, Integer, DateTime, text
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue

TABLE_NAME = 'runtime'


def declare(base, prefix):
    table_name = f'{prefix}_{TABLE_NAME}'

    class Runtime(base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        last_checked_timestamp = Column(DateTime)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())
    return Runtime
