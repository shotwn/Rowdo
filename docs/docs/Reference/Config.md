# Configuration
## Config.ini
Rowdo uses the `config.ini` file on it's script or executable directory for global configuration parameters.
### Fields
#### Database
``` ini
[database]
    user = my_username
    password = my_very_complex_password
    database = database
    host = hostname
; or
;    url = mysql://my_username:my_very_complex_password@hostname/dbname
; optionally
    table_prefix = rowdo
```

##### User
`user` required if not [database.url](#url) \
string

Username for the mysql engine.
``` ini
user = my_username
```
##### Password
`password` required if not [database.url](#url) \
string

Password for the mysql engine.
``` ini
password = my_very_complex_password
```
##### Database
`database` required if not [database.url](#url) \
string

Database for the mysql engine.
``` ini
database = database
```
##### Host
`host` required if not [database.url](#url) \
string

Host address for the mysql engine.
``` ini
host = hostname
```
##### URL
`url` required if not [user:](#user)[password](#password)[@database](#database)[.host](#host) \
string

SQLAlchemy Engine connection string, replaces mysql engine parameters if set.
``` ini
url = mysql://my_username:my_very_complex_password@hostname/dbname
```
##### Table Prefix
`table_prefix` optional \
string `default: rowdo`

Prefix used front of tables in database. Such as `rowdo_files`.
``` ini
table_prefix = rowdo
```

#### Download
``` ini
; all optional
[download]
    disallow_from = example.com
    allow_from = *
    allow_formats_url = *
    path = files
    keep_relative_path = 1
    allow_mime_types = *
    max_attempts = 3
```

##### Disallow From
`disallow_from` optional\
string `default: (empty string)`

Comma separated list of disallowed websites. Can include protocol such as `http://example.com`.

!!! info
    Disallowed patterns checked before allowed ones in [allow from](#allow-from) hence overriding it.

``` ini
; ban all non secure downloads
disallow_from = http://
```
##### Allow From
`disallow_from` optional\
string `default: *`

Comma separated list of allowed websites.

!!! info
    Default * wildcard allows every url which are not in [disallow from](#disallow-from) list.

```ini
allow_from = *
```

##### Allowed Formats URL
`allow_formats_url` optional\
string `default: *`

Comma separated list of URL ends. Default * wildcard disables this check. When enabled it allows only URLs which end with `.format` are allowed.

```ini
allow_formats_url = *
```

##### Path
`path` optional\
string `default: files`

Path relative to current working directory (where .exe is) to save files. At the moment upper directories such as `..\.` are not allowed.

Path value is included in files table's [downloaded_path](Tables.md#downloaded-path) field.

!!! Example
    If `row.file_name` is set `example.png` and `config.path` is set `files` then;\
    `row.downloaded_path` in relative mode will be `files\example.png`

``` ini
path = files
```

##### Keep Relative Path
`keep_relative_path` optional\
boolean `default: 1`

Determines the record type of [downloaded_path](Tables.md#downloaded-path) field.

When this settings is set to `0`, [downloaded_path](Tables.md#downloaded-path) will be a full path such as `C:\current working directory\files\example.png`. 

!!! Danger
    This setting shouldn't change after first file is downloaded.

!!! Warning
    Using this option might be dangerous, allowing internal filesystem information in database.

``` ini
keep_relative_path = 1
```

##### Allow MIME Types
`allow_mime_types` optional\
string `default: *`

Comma separated list of allowed [MIME types](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types){target=_blank}. Default `*` wildcard disables this check.

``` ini
allow_mime_types = *
; example
allow_mime_types = image/jpeg, image/png
```

##### Maximum Attempts
`max_attempts` optional\
integer `default: 3`

Maximum number of retries on connection errors.

```ini
max_attempts = 3
```

#### Runtime
``` ini
[runtime]
    debug = 0
    run_every_seconds = 10
```

##### Debug
`debug` optional \
boolean `default: 0`

Enables debug mode.
``` ini
debug = 0
```

##### Run Every Seconds
`run_every_seconds` optional \
integer `default: 10`

Period of the main loop checking the database.
``` ini
run_every_seconds = 10
```

##### Working Directory
`working_directory` optional \
integer `default: executable or script call location`

Main directory for program to work in. [Download directory](#path) and logs are relative to this directory.
Normally these are relative to `Rowdo.exe` or when run as script to cwd.
``` ini
working_directory = C:\my other directory
```
## Examples
### Bare Minimums
``` ini
; config.ini
[database]
    user = my_username
    password = my_very_complex_password
    database = database
    host = hostname
```

### Only Images from Imageshack
``` ini
; config.ini
[database]
    user = my_username
    password = my_very_complex_password
    database = database
    host = hostname
[download]
    path = files\rowdo
; allow_from is not '*' anymore. only these will be allowed.
    allow_from = https://imagizer.imageshack.com
; allow_formats_url is not '*' anymore. only these will be allowed.
    allow_formats_url = png, jpg
    allow_mime_types = image/jpeg, image/png
```
