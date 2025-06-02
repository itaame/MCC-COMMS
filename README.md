Packaging
pyinstaller --noconsole --onefile --add-data "certs;certs" bot_server.py 
pyinstaller --noconsole --onefile --add-data "logo.png;." --add-data "logo2.png;." --add-data "soundwave.py;." --add-data "certs;certs" --add-data "LOOPS;LOOPS" gui.py
pyinstaller --noconsole --onefile --icon=logo2.ico --add-data "certs;certs" --add-data "config_dialog.py;." --add-data "LOOPS;LOOPS" start_all.py

To make a "double-clickable" .app for GUI apps, use the --windowed and --name flags:

pyinstaller --onefile --windowed --icon=logo2.icns start_all.py
pyinstaller --onefile --add-data="logo.png:." --add-data="logo2.png:." --add-data="soundwave.py:." gui.py
pyinstaller --onefile --add-data="certs:certs" bot_server.py                  
