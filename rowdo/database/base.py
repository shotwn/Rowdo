class RowdoBase(object):
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mariadb_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
        'mariadb_charset': 'utf8'
    }
