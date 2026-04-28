import json
import time
import threading
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ConfigWatcher:
    """Отслеживает изменения в settings.json и уведомляет подписчиков"""

    def __init__(self, config_path='config/settings.json'):
        self.config_path = config_path
        self.observers = []
        self.callbacks = []
        self.running = False
        self.observer = None

    def start_watching(self):
        """Запускает отслеживание изменений файла"""
        if self.running:
            return

        self.running = True

        # Определяем полный путь к файлу
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, self.config_path)
        config_dir = os.path.dirname(full_path)

        class SettingsHandler(FileSystemEventHandler):
            def __init__(self, watcher):
                self.watcher = watcher

            def on_modified(self, event):
                if event.src_path == full_path:
                    print(f"Settings file changed: {event.src_path}")
                    self.watcher.reload_settings()

        event_handler = SettingsHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=config_dir, recursive=False)
        self.observer.start()
        print(f"Started watching config file: {full_path}")

    def stop_watching(self):
        """Останавливает отслеживание"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def reload_settings(self):
        """Перезагружает настройки и уведомляет подписчиков"""
        try:
            # Определяем путь к файлу
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, self.config_path)

            with open(full_path, 'r', encoding='utf-8') as f:
                new_settings = json.load(f)

            print("Settings reloaded successfully")

            # Уведомляем всех подписчиков
            for callback in self.callbacks:
                callback(new_settings)

        except Exception as e:
            print(f"Error reloading settings: {e}")

    def subscribe(self, callback):
        """Подписывает функцию на изменения настроек"""
        self.callbacks.append(callback)

    def unsubscribe(self, callback):
        """Отписывает функцию"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)