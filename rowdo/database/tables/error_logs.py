from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue


TABLE_NAME = 'error_logs'


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

    class ErrorLog(base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        belongs_to = Column(Integer, ForeignKey(f'{prefix}_files.id', ondelete="CASCADE"))
        type = Column(Text)
        message = Column(Text)
        level = Column(Integer)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())
        parent = relationship('File', back_populates="errors", viewonly=False)
    return ErrorLog
