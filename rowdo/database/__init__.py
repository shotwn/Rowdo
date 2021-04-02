from datetime import datetime

from mysql.connector import connect, Error

from rowdo.logging import logger
import rowdo.config as config


COMMAND_IDLE = 0
COMMAND_DOWNLOAD = 1
COMMAND_DELETE = 2
COMMAND_DELETE_FILE_ONLY = 3
COMMAND_DELETE_ROW_ONLY = 4

STATUS_WAITING_TO_PROCESS = 0
STATUS_PROCESSING = 1
STATUS_DONE = 2
STATUS_ERROR = 3

RESIZE_NONE = -1
RESIZE_PASSTHROUGH = 0
RESIZE_DIMENSIONS = 1
RESIZE_RATIO = 2


class Database:
    def __init__(self):
        self.connected = False
        self._prefix = config.get('database', 'table_prefix')
        self.tables = {
            f'{self._prefix}_files': {
                'id': {
                    'type': 'INT',
                    'KEY': 'PRIMARY KEY',
                    'NULL': False,
                    'AUTO INCREMENT': True
                },
                'url': {
                    'type': 'TEXT'
                },
                'path': {
                    'type': 'TEXT',
                    'NULL': True
                },
                'filename': {
                    'type': 'TEXT',
                    'NULL': True
                },
                'resize_mode': {
                    'type': 'INT',
                    'DEFAULT': '-1'
                },
                'resize_width': {
                    'type': 'INT',
                    'NULL': True
                },
                'resize_height': {
                    'type': 'INT',
                    'NULL': True
                },
                'resize_ratio': {
                    'type': 'DECIMAL(10,5)',
                    'NULL': True
                },
                'command': {
                    'type': 'INT',
                    'DEFAULT': '1'  # 0: do nothing, 1: download, 2:delete_all, 3: delete_file, 4:delete_row
                },
                'status': {
                    'type': 'INT',
                    'DEFAULT': '0'
                },
                'preset_id': {
                    'type': 'INT',
                    'DEFAULT': '-1'
                },
                'created_at': {
                    'type': 'TIMESTAMP',
                    'DEFAULT': 'CURRENT_TIMESTAMP'
                },
                'updated_at': {
                    'type': 'TIMESTAMP',
                    'DEFAULT': 'CURRENT_TIMESTAMP',
                    'ATTRIBUTES': 'on update CURRENT_TIMESTAMP'
                }
            },
            f'{self._prefix}_runtime': {
                'id': {
                    'type': 'INT',
                    'KEY': 'PRIMARY KEY',
                    'NULL': False
                },
                'last_checked_timestamp': {
                    'type': 'TIMESTAMP',
                    'NULL': True
                }
            }
        }

    def connect(self, check_tables=True):
        logger.info('Connecting database...')
        self.cnx = connect(
            host=config.get('database', 'host'),
            user=config.get('database', 'user'),
            password=config.get('database', 'password'),
            database=config.get('database', 'database')
        )

        self.cursor = self.cnx.cursor
        self.connected = True

        if check_tables:
            self.check_tables()

    def connect_if_not_connected(self):
        if not self.connected:
            self.connect()

    def check_tables(self):
        sql = 'SHOW TABLES'
        with self.cursor() as cursor:
            cursor.execute(sql)
            db_tables_tuples = cursor.fetchall()
            self.cnx.commit()
            db_tables = [c[0] for c in db_tables_tuples]

            for table_name in self.tables.keys():
                if not db_tables or table_name not in db_tables:
                    self.create_table(table_name)
            logger.info('Tables checked.')

    def create_table(self, table_name):
        table_structure = self.tables[table_name]
        columns = []
        keys = []
        for member_name, member in table_structure.items():
            fields = []

            fields.append(f'`{member_name}` {member["type"]}')

            if member.get('ATTRIBUTES'):
                fields.append(member.get('ATTRIBUTES'))

            fields.append('NULL' if member.get('NULL') else 'NOT NULL')

            if member.get('AUTO INCREMENT'):
                fields.append('AUTO_INCREMENT')

            default = member.get('DEFAULT')
            if default or isinstance(default, bool):
                if default in ['CURRENT_TIMESTAMP', 'NULL'] or isinstance(default, bool):
                    fields.append(f'DEFAULT {str(default).upper()}')
                else:
                    fields.append(f'DEFAULT \'{default}\'')

            if member.get('KEY'):
                keys.append(f'{member.get("KEY")} (`{member_name}`)')

            columns.append(' '.join(fields))

        # This is all internal, don't expect sql injection
        sql = f'CREATE TABLE {table_name} ({", ".join(columns + keys)}) ENGINE = InnoDB;'

        logger.info(f'Creating table {table_name}\n{sql}')
        with self.cursor() as cursor:
            cursor.execute(sql)
            self.cnx.commit()

    def read_file_rows(self, status=0, last_checked_timestamp: datetime = None):
        ts_check = ''
        if last_checked_timestamp:
            ts_check = f" AND updated_at > '{last_checked_timestamp.isoformat()}'"

        ts_check = ''  # ! For debug only

        sql = f'SELECT * FROM {self._prefix}_files WHERE status = {status}{ts_check} ORDER BY updated_at ASC'
        print(sql)
        files = []
        with self.cursor(dictionary=True) as cursor:
            try:
                cursor.execute(sql)
                files = cursor.fetchall()
                self.cnx.commit()
            except Error as err:
                logger.error(err)
                logger.debug(cursor.statement)
                raise err

        return files

    def update_file_row(self, id, fields_and_values: dict):
        update_str = []
        update_data = {
            'id': id
        }
        for key, value in fields_and_values.items():
            update_str.append(f'{key} = %({key}__val)s')  # Consider: Escaping the key.
            update_data[f'{key}__val'] = value

        sql = f"UPDATE {self._prefix}_files SET {', '.join(update_str)} WHERE id = %(id)s"

        with self.cursor() as cursor:
            try:
                cursor.execute(sql, update_data)
                self.cnx.commit()
            except Error as err:
                logger.error(err)
                raise err

    def delete_file_row(self, id):
        query_data = {
            'id': id
        }
        sql = f"DELETE FROM {self._prefix}_files WHERE id = %(id)s"
        with self.cursor() as cursor:
            try:
                cursor.execute(sql, query_data)
                self.cnx.commit()
            except Error as err:
                logger.error(err)
                raise err

    def set_runtime(self, fields_and_values: dict):
        fields_and_values['id'] = 1
        sql = f"REPLACE INTO {self._prefix}_runtime ({', '.join(fields_and_values.keys())}) VALUES ({', '.join([f'%({key})s' for key in fields_and_values.keys()])})"
        with self.cursor() as cursor:
            try:
                cursor.execute(sql, fields_and_values)
                self.cnx.commit()
            except Error as err:
                logger.error(err)
                logger.debug(cursor.statement)
                raise err

    def get_runtime(self):
        sql = f"SELECT * FROM {self._prefix}_runtime WHERE id = 1"
        with self.cursor(dictionary=True) as cursor:
            try:
                cursor.execute(sql)
                runtime = cursor.fetchone()
                self.cnx.commit()
                return runtime
            except Error as err:
                logger.error(err)
                logger.debug(cursor.statement)
                raise err
