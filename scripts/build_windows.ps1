New-Item -Path .\win-build -ItemType directory

..\env\scripts\activate

cd .\win-build

pyinstaller.exe --onefile --runtime-tmpdir=. --hidden-import win32timezone ..\..\windows.py

deactivate

cd ..