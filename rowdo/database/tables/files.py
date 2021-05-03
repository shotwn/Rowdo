from sqlalchemy import Column, Integer, Text, Numeric, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue

TABLE_NAME = 'files'


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

    class File(base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        url = Column(Text, nullable=False)
        downloaded_path = Column(Text)
        filename = Column(Text)
        resize_mode = Column(Integer, server_default='-1', nullable=False)
        resize_width = Column(Integer)
        resize_height = Column(Integer)
        resize_ratio = Column(Numeric(10, 5))
        command = Column(Integer, server_default='1', nullable=False)
        status = Column(Integer, server_default='0', nullable=False)
        failed_attempts = Column(Integer, server_default='0', nullable=False)
        preset_id = Column(Integer)
        created_at = Column(DateTime, server_default=func.now(), nullable=False)
        updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue(), nullable=False)
        errors = relationship('ErrorLog', back_populates="parent", viewonly=False)
    return File
