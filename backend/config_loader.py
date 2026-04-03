import json
import os

class Config:
    """Класс для загрузки и доступа к настройкам"""

    def __init__(self, config_path='config/settings.json'):
        self.config_path = config_path
        self.data = self.load_config()

    def load_config(self):
        """Загружает настройки из JSON файла"""
        try:
            # Определяем путь к файлу настроек
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, self.config_path)

            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл настроек не найден: {self.config_path}")
            return
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return


    def get(self, key, default=None):
        """Получает значение по ключу с точкой (например, 'camera.width')"""
        keys = key.split('.')
        value = self.data
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default


# Создаем глобальный экземпляр конфигурации
config = Config()