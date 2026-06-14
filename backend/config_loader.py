import json
import os
import threading


class Config:
    # Сервис загрузки настроек

    def __init__(self, config_path='config/settings.json'):
        self.config_path = config_path
        self.data = {}
        self.lock = threading.Lock()
        self.callbacks = []
        self.load_config()


        self.watcher = None

    def load_config(self):

        try:
            # Определяем путь к файлу настроек
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, self.config_path)

            with open(full_path, 'r', encoding='utf-8') as f:
                new_data = json.load(f)

            with self.lock:
                self.data = new_data

            # Уведомляем подписчиков об изменениях
            for callback in self.callbacks:
                callback(self.data)

            print(f"Config loaded from: {full_path}")
            return True

        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return False

    def reload(self):

        return self.load_config()

    def get(self, key, default=None):
        # Получает значение по ключу с точкой
        keys = key.split('.')

        with self.lock:
            value = self.data

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_all(self):
        # Возвращает все настройки
        with self.lock:
            return self.data.copy()

    def subscribe(self, callback):
        # Подписывает функцию на изменения настроек
        self.callbacks.append(callback)

    def unsubscribe(self, callback):
        # Отписывает функцию
        if callback in self.callbacks:
            self.callbacks.remove(callback)


# Создаем глобальный экземпляр конфигурации
config = Config()