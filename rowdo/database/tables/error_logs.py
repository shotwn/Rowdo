from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import FetchedValue


TABLE_NAME = 'error_log'


def declare(base, prefix):
    table_name = f'{prefix}_{TABLE_NAME}'

    class ErrorLog(base):
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        belongs_to = Column(Integer, ForeignKey(f'{prefix}_files.id'))
        type = Column(Text)
        message = Column(Text)
        level = Column(Integer)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())
        parent = relationship('File', back_populates="errors", viewonly=False)
    return ErrorLog
