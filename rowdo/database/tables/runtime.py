from sqlalchemy import Column, Integer, DateTime, text
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue

TABLE_NAME = 'runtime'


def declare(base, prefix, table_name=TABLE_NAME):
    """Create a declared instance of SqlAlchemy Table

    Args:
        base (sqlalchemy.ext.declarative.declarative_base()): SqlAlchemy Declarative Base
        prefix (str): Global table prefix
        table_name (str, optional): Table name. Defaults to TABLE_NAME.

    Returns:
        sqlalchemy.ext.declarative.declarative_base(): SqlAlchemy Table
    """
    table_name = f'{prefix}_{table_name}'

    class Runtime(base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        last_checked_timestamp = Column(DateTime)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())
    return Runtime
