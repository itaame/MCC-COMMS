Packaging
pyinstaller --noconsole --onefile --add-data "certs;certs" bot_server.py
pyinstaller --noconsole --onefile --add-data "logo.png;." --add-data "logo2.png;." --add-data "soundwave.py;." --add-data "certs;certs" gui.py
pyinstaller --noconsole --onefile --icon=logo2.ico --add-data "certs;certs" start_all.py

To make a "double-clickable" .app for GUI apps, use the --windowed and --name flags:
