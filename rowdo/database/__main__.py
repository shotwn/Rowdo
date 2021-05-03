from rowdo.config import DEFAULTS
from rowdo.database import Database, STATUS_ERROR
from rowdo.exceptions import RowdoException

DEFAULTS['database']['table_prefix'] = 'test_rowdo'
db = Database()

print('RUNNING DB TESTS')
print(db.read_file_rows())

session = db.session()
files = db.get_table('files')
new_file = files(
    url='https://imagizer.imageshack.com/img924/4792/08aHah.png'
)
session.add(new_file)

session.commit()

db.register_error(new_file, RowdoException('test_error'))

db.update_file_row(new_file, {'status': STATUS_ERROR})
