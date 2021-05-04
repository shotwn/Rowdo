from datetime import datetime

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, declarative_base

from rowdo.database.base import RowdoBase
from rowdo.logging import logger
import rowdo.config as config
import rowdo.exceptions
from rowdo.version import __schema_version__

import rowdo.database.tables

COMMAND_IDLE = 0
COMMAND_DOWNLOAD = 1
COMMAND_DELETE = 2
COMMAND_DELETE_FILE_ONLY = 3
COMMAND_DELETE_ROW_ONLY = 4

STATUS_WAITING_TO_PROCESS = 0
STATUS_PROCESSING = 1
STATUS_DONE = 2
STATUS_ERROR = 3
STATUS_WILL_RETRY = 4
STATUS_MAX_RETRIES_REACHED = 5

RESIZE_NONE = -1
RESIZE_PASSTHROUGH = 0
RESIZE_DIMENSIONS = 1
RESIZE_RATIO = 2


class Database:
    def __init__(self):
        self._prefix = config.get('database', 'table_prefix')
        connect_url = config.get('database', 'url')
        if not connect_url:
            host = config.get('database', 'host')
            user = config.get('database', 'user')
            password = config.get('database', 'password')
            database = config.get('database', 'database')

            connect_url = f"mysql://{user}:{password}@{host}/{database}"
        self._engine = create_engine(connect_url, echo=False, future=True, encoding='utf-8')

        self._session_maker = sessionmaker(bind=self._engine)
        self._declarative_base = declarative_base(cls=RowdoBase)

        self.tables = {}
        for module in rowdo.database.tables.modules:
            orm_class = module.declare(self._declarative_base, self._prefix)
            name = module.TABLE_NAME
            self.tables[name] = orm_class

        self._declarative_base.metadata.create_all(self._engine)
        self._session = None

        self._cleanup_processing_rows()

    def get_table(self, name):
        return self.tables[name]

    def session(self):
        if not self._session:
            self.begin_session()

        return self._session

    def begin_session(self):
        logger.debug('SQLAlchemy New Session')
        self._session = self._session_maker()
        self._session.commit()

    def close_session(self):
        logger.debug('SQLAlchemy Close Session')
        if self._session:
            self._session.close()
            self._session = None

    def _update_row(self, orm, fields_and_values: dict):
        for key, value in fields_and_values.items():
            setattr(orm, key, value)

    def _cleanup_processing_rows(self):
        """Reverts the status=STATUS_processing rows back to STATUS_WAITING_TO_PROCESS
        Call at first run.
        """
        session = self.session()
        files = self.get_table('files')
        stuck = session.query(files).filter(files.status == STATUS_PROCESSING)
        for file_row in stuck:
            file_row.status = STATUS_WAITING_TO_PROCESS
        session.commit()
        self.close_session()

    def read_file_rows(self, status, last_checked_timestamp: datetime = None):
        session = self.session()
        files = self.get_table('files')
        arguments = []
        if isinstance(status, int):
            status = [status]
        elif not isinstance(status, list):
            raise ValueError('arg. "status" is not correct type.')

        if last_checked_timestamp:
            arguments.append(files.updated_at > last_checked_timestamp)

        query = session.query(files).filter(*arguments, files.status.in_(status)).order_by(asc(files.updated_at))

        return query

    def update_file_row(self, file_row, fields_and_values: dict):
        session = self.session()
        self._update_row(file_row, fields_and_values)
        session.commit()

    def delete_file_row(self, file_row):
        session = self.session()
        session.delete(file_row)
        session.commit()

    def set_runtime(self, fields_and_values: dict):
        session = self.session()
        runtime = self.get_table('runtime')
        exists = session.query(runtime).filter(runtime.id == 1).one_or_none()
        if not exists:
            logger.warning('Creating Runtime')
            new = runtime(id=1, schema_version=__schema_version__, **fields_and_values)
            session.add(new)
        else:
            self._update_row(exists, fields_and_values)
        session.commit()

    def get_runtime(self):
        runtime = self.get_table('runtime')
        session = self.session()
        return session.query(runtime).filter(runtime.id == 1).one_or_none()

    def register_error(self, file, error):
        session = self.session()
        error_logs = self.get_table('error_logs')

        if getattr(error, 'level', False):
            lvl = error.level
        else:
            lvl = rowdo.exceptions.CRITICAL

        session.add(error_logs(
            belongs_to=file.id,
            message=error.message,
            type=type(error).__name__,
            level=lvl
        ))
        session.commit()
