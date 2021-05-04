# Windows Specific
## Executable
Windows executable runs by simply:
``` ps1
rowdo.exe
```
Exe can also be installed as a service.

## Service API

### Install
``` ps1
rowdo.exe --service install
```
Or for automatic service start on logon. (Default is manual)
``` ps1
rowdo.exe --startup auto --service install
```

### Update
``` ps1
rowdo.exe --service update
```
To change start up option
``` ps1
rowdo.exe --service --startup delayed update
```
``` ps1
rowdo.exe --service --startup disabled update
```
``` ps1
rowdo.exe --service --startup manual update
```

### Start
``` ps1
rowdo.exe --service start
```

### Stop
``` ps1
rowdo.exe --service stop
```

### Remove
``` ps1
rowdo.exe --service remove
```