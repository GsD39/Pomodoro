import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, Qt
from pygame import mixer
from ui.main_window import Ui_MainWindow


from PyQt5.QtCore import QThread, pyqtSignal
import keyboard

class HotkeyThread(QThread):
    hotkey_triggered = pyqtSignal()  # Сигнал для связи с главным потоком

    def __init__(self, hotkey):
        super().__init__()
        self.hotkey = hotkey
        self.running = True

    def run(self):
        # Регистрируем хоткей
        keyboard.add_hotkey(self.hotkey, self._handle_hotkey)

        # Бесконечный цикл для поддержания работы
        while self.running:
            keyboard.wait()  # Ожидаем события

    def _handle_hotkey(self):
        self.hotkey_triggered.emit()  # Отправляем сигнал в главный поток

    def stop(self):
        self.running = False
        keyboard.unhook_all()  # Очищаем хоткеи


class PomodoroApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Инициализация
        self.settings_file = "settings.json"
        self.is_running = False
        self.current_stage = "work"
        self.stage_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.settings = None
        mixer.init()

        self.hotkey = None
        self.sound_files = None
        self.work_time = None
        self.short_break_time = None
        self.long_break_time = None

        # Загрузка настроек
        self.load_settings()

        # Настройка интерфейса
        self.start_button.clicked.connect(self.toggle_timer)
        self.setWindowTitle("Pomodoro Timer")
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))  # Укажите путь к иконке

        # Создаем контекстное меню для трея
        self.tray_menu = QMenu()

        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show_normal)
        self.tray_menu.addAction(show_action)

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.true_exit)
        self.tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)

        # Обработка клика по иконке трея
        self.tray_icon.activated.connect(self.tray_icon_clicked)


        # Глобальные горячие клавиши
        self.hotkey_thread = HotkeyThread(hotkey=self.hotkey)
        self.hotkey_thread.hotkey_triggered.connect(self.toggle_timer)
        self.hotkey_thread.start()

        # Установка начальных значений
        self.work_duration.setValue(int(self.work_time))
        self.short_break_duration.setValue(int(self.short_break_time))
        self.long_break_duration.setValue(int(self.long_break_time))

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def true_exit(self):
        # Остановка всех потоков и процессов
        if hasattr(self, 'hotkey_thread'):
            self.hotkey_thread.stop()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def load_settings(self):
        """Загрузка настроек из файла"""
        default_settings = {
            "hotkey": "ctrl+shift+p",
            "sounds": {
                "work": "sounds/work_complete.wav",
                "short_break": "sounds/short_break.wav",
                "long_break": "sounds/long_break.wav"
            },
            "times": {
                "work": 25,
                "short_break": 5,
                "long_break": 15
            }
        }

        try:
            with open(self.settings_file, "r") as f:
                self.settings = json.load(f)
        except Exception as e:
            print(e)
            self.settings = default_settings
            with open(self.settings_file, "w") as f:
                json.dump(default_settings, f, indent=4)

        self.hotkey = self.settings["hotkey"]
        self.sound_files = self.settings["sounds"]
        self.work_time = self.settings["times"]["work"]
        self.short_break_time = self.settings["times"]["short_break"]
        self.long_break_time = self.settings["times"]["long_break"]

    def save_settings(self):
        """Сохранение настроек в файл"""
        self.settings["times"]["work"] = int(self.work_duration.text())
        self.settings["times"]["short_break"] = int(self.short_break_duration.text())
        self.settings["times"]["long_break"] = int(self.long_break_duration.text())

        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=4)

    def play_sound(self, stage):
        """Воспроизведение звука для этапа"""
        sound_file = self.sound_files.get(stage)
        if sound_file and os.path.exists(sound_file):
            mixer.music.load(sound_file)
            mixer.music.play()

    def start_timer(self):
        """Запуск таймера"""
        self.is_running = True
        self.start_button.setText("Пауза")
        self.save_settings()
        self.timer.start()

        # Определение текущего этапа
        if not hasattr(self, 'time_left'):
            if self.current_stage == "work":
                self.time_left = self.work_time * 60
            elif self.current_stage == "short_break":
                self.time_left = self.short_break_time * 60
            else:
                self.time_left = self.long_break_time * 60

        self.timer.start(1000)  # Обновление каждую секунду

    def stop_timer(self):
        """Остановка таймера"""
        self.is_running = False
        self.start_button.setText("Старт")
        self.timer.stop()

    def toggle_timer(self):
        """Переключение состояния таймера"""
        if self.is_running:
            self.stop_timer()
        else:
            self.start_timer()

    def update_timer(self):
        """Обновление таймера"""
        self.time_left -= 1

        # Форматирование времени MM:SS
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Окончание этапа
        if self.time_left <= 0:
            self.timer.stop()
            self.next_stage()

    def next_stage(self):
        """Переключение на следующий этап"""
        if self.current_stage == "work":
            self.stage_count += 1
            if self.stage_count % 4 == 0:
                self.current_stage = "long_break"
                self.time_left = self.long_break_time * 60
            else:
                self.current_stage = "short_break"
                self.time_left = self.short_break_time * 60
        else:
            self.current_stage = "work"
            self.time_left = self.work_time * 60
        self.play_sound(self.current_stage)
        self.statusBar().showMessage(f"Этап: {'Работа' if self.current_stage == 'work' else 'Перерыв'}", 3000)

    def tray_icon_activated(self, reason):
        """Обработка действий в системном трее"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        event.ignore()
        self.hide()
        self.tray_icon.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Проверка на повторный запуск
    if QApplication.instance() is not None:
        app.setQuitOnLastWindowClosed(False)

    window = PomodoroApp()
    window.show()
    sys.exit(app.exec_())
