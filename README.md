**How to use:**

git clone https://github.com/GsD39/Pomodoro

cd Pomodoro

python -m venv build_env

build_env\Scripts\activate

pip install pyinstaller 

pip install -r requirements.txt

pyinstaller --onefile --windowed --icon=icon.ico --add-data "settings.json:." --add-data "sounds/:sounds/" main.py

xcopy sounds dist\\sounds /i

xcopy icon.png dist

xcopy settings.json dist

**Now you can run main.exe, it's in \dist**

**Be cautious - if you move main.exe somewhere, move sounds, icon and settings with it**


*P.S.*
*I prefer to add it into autoload*
