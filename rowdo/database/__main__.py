from rowdo.config import DEFAULTS
from rowdo.database import Database

DEFAULTS['database']['table_prefix'] = 'test_rowdo'
db = Database()

print(db.read_file_rows())
