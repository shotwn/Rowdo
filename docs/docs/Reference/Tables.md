# Tables
## Files Table
| Field           | Type           | Default            | Insert / Update | Nullable |
| --------------- | -------------- | ------------------ | --------------- | -------- |
| id              | Integer        | AUTO - PRIMARY KEY | No              |          |
| url             | Text           |                    | Yes             | No       |
| filename        | Text           |                    | Yes             |          |
| resize_mode     | Integer        | -1                 | Yes             | No       |
| resize_width    | Integer        |                    | Yes             |          |
| resize_height   | Integer        |                    | Yes             |          |
| resize_ratio    | Numeric(10, 5) |                    | Yes             |          |
| command         | Integer        | 1                  | Yes             | No       |
| status          | Integer        | 0                  | Yes*            | No       |
| failed_attempts | Integer        | 0                  | Yes*            | No       |
| preset_id       | Integer        |                    | Yes             |          |
| downloaded_path | Text           |                    | No              |          |
| created_at      | DateTime       | CURRENT_TIMESTAMP  | No              | No       |
| updated_at      | DateTime       | CURRENT_TIMESTAMP  | No              | No       |
*: Only for RESET

### Fields
#### Url
URL for the item to be downloaded. It cannot be blank.

#### Filename
File name for the downloaded file. If not set rowdo will generate the file name from URL and save the file directly on top level directory.

File name field can contain directories such as `\events\2002` or `\events\2002.12.02.jpg`. Directories will be automatically created inside the save directory.

!!! warning
    Currently rowdo doesn't do any uniqueness checks on file names. So make sure to check database before entering a new file name. Using the same file name twice will override the already existing file.

##### Extensions
If not present, Rowdo will try to assign an extension to saved file automatically using the URL or MIME Type. For example `\events\2002` will be saved as `\events\2002.jpg`.

If filename is set and contains one or more dots, string after the last dot will be assumed as the save extension. For example with `\events\2002.12.02` `02` would be assumed as extension.

If any of the resize modes is active, PIL library will try to re-format the downloaded contents as the set format. So even if downloaded picture is a JPG, it can be saved as a PNG by giving `.png` extension to filename as long as resize is active. If resize is not active, downloaded content will still have the `.png` extension but it will not be in PNG format.

!!! warning
    It is highly recommended to provide a full filename with an extension.

#### Resize Mode
Sets the resize mode.
!!! info inline "Resize Modes"
    | Value | Mode        |
    | ----- | ----------- |
    | -1    | None        |
    | 0     | Passthrough |
    | 1     | Dimensions  |
    | 2     | Ratio       |

##### Passthrough
Saves the file using PIL library without any resize.

##### Dimensions
Resizes the file according to resize_width and resize_height.

##### Ratio
Resizes the file according to resize_ratio.

<div style="clear: both"> </div>

#### Command
Main commands available in rowdo for the row.
!!! info inline end "Commands"
    | Value | Command              |
    | ----- | -------------------- |
    | 0     | Idle                 |
    | 1     | Download             |
    | 2     | Delete               |
    | 3     | Delete File Only     |
    | 4     | Delete DB Entry Only |

- Idle command gives done status but does not process the row any further.
- Download command downloads the file in the next run.
- Delete command deletes both the file and the row. Delete file only and Delete DB entry only commands do partial deletes.

<div style="clear: both"> </div>

#### Status
Status codes are the main tracking and triggering mechanism for rowdo. Rowdo processes rows only when their status codes are in `Waiting to Process` or `Will Retry` modes.
!!! info inline "Status Codes"
    | Value | Status              |
    | ----- | ------------------- |
    | 0     | Waiting to Process  |
    | 1     | Processing          |
    | 2     | Done                |
    | 3     | Error               |
    | 4     | Will Retry          |
    | 5     | Max Retries Reached |

##### Waiting to Process
Default RESET state for the rowdo. For processing to start with any [command](#command) status code should be `Waiting to process` or `Will Retry`. It is important to understand that changing the command will not trigger any processing as long as status is not RESET to this value.

##### Processing
Indicates the given command being processed. If rowdo will get terminated when a process is not complete, at next run all processing statuses will be reverted back to [waiting to process](#waiting-to-process).

##### Done
Set command is successfully completed.

##### Error
A critical error happened and processing of this row has been terminated. This will create an error entry in [error logs table](#error-logs-table).

##### Will Retry
A warning level error happened and processing of this row has been terminated. This status is generally generated in non-configuration-related errors, such as a network error. An error can be found in [error logs table](#error-logs-table).

Rowdo will try the process this row again in next run until the maximum set number of retries in the config.ini has been reached.

##### Max Retries Reached
Indicates the error which created the [will retry](#will-retry) code was not resolved until maximum tries have been reached. Processing has been stopped.

#### Failed Attempts
Indicates the failed attempts in processing of this file. It shouldn't be rewritten unless problem was solved and a RESET with multiple tries allowed is being made.

#### Preset ID
Reserved field for possible future per-item configuration feature.

#### Downloaded Path
Where the file is located in the file system. It can be a relative path or an absolute path depending on corresponding configuration in `config.ini`.

#### Created At
Required field to keep track of the row. In mysql, rowdo enables `CURRENT_TIMESTAMP` default. So created date is automatically set during INSERT and user does not have to create this field manually.

#### Updated At
Required field to keep track of changes happening to row commands. Rowdo will remember the latest checked row and will not check rows which are updated before it.

In mysql, rowdo enables `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` defaults, so user does not have to create/modify this field manually on every insert/update.

## Error Logs Table
Read only table of errors occurred during processing of rows.

!!! Warning
    This table does not include system level errors, such as configuration or file permission errors. Check log files in `.\logs\` for these.

### Fields

| Field      | Type     | Nullable |
| ---------- | -------- | -------- |
| id         | Integer  | No       |
| belongs_to | Integer  | No       |
| type       | text     | Yes      |
| message    | text     | Yes      |
| level      | text     | Yes      |
| created_at | DateTime | No       |
| updated_at | DateTime | No       |

#### Belongs To
A foreign key representing a row in [files table](#files-table).

#### Type
Represents an exception type.

#### Level
Represents a severity level.
```python
severities = {
    'CRITICAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    'INFO': 20,
    'DEBUG': 10,
    'TRACE': 5,
    'NOTSET': 0
}
```

# Runtime Table
Runtime table is a 1 row table which keeps internal parameters for rowdo throughout sessions.
## Fields
| Field                  | Type     | Description                         |
| ---------------------- | -------- | ----------------------------------- |
| id                     | Integer  | Always 1                            |
| last_checked_timestamp | Integer  | Timestamp of the last processed row |
| schema_version         | Text     | Active database schema version      |
| created_at             | DateTime |                                     |
| updated_at             | DateTime |                                     |
