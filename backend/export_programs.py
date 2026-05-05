import os
import sys
import winreg
import json
from datetime import datetime


def normalize_path(path):
    """
    Нормализует путь: убирает лишние слеши, приводит к стандартному виду
    """
    if not path:
        return path

    # Убираем слеш в конце, если он есть
    path = path.rstrip('\\/')

    # Нормализуем путь (преобразуем / в \ и т.д.)
    path = os.path.normpath(path)

    return path


def get_program_exe_path(app_key):
    """
    Получает путь к исполняемому файлу программы
    Приоритет: DisplayIcon > InstallLocation + поиск exe
    """
    exe_path = None

    # Сначала пытаемся получить из DisplayIcon
    try:
        display_icon = winreg.QueryValueEx(app_key, "DisplayIcon")[0]
        if display_icon:
            # Извлекаем путь из DisplayIcon (иногда там есть запятая с номером ресурса)
            if ',' in display_icon:
                exe_path = display_icon.split(',')[0]
            else:
                exe_path = display_icon

            exe_path = normalize_path(exe_path)

            # Проверяем, что это файл .exe
            if exe_path and os.path.exists(exe_path) and exe_path.lower().endswith('.exe'):
                return exe_path
    except (WindowsError, FileNotFoundError, OSError):
        pass

    # Если не получили из DisplayIcon, пробуем InstallLocation
    try:
        install_location = winreg.QueryValueEx(app_key, "InstallLocation")[0]
        if install_location:
            install_location = normalize_path(install_location)
            if os.path.exists(install_location):
                # Пробуем найти .exe файлы в папке установки
                for root, dirs, files in os.walk(install_location):
                    for file in files:
                        if file.lower().endswith('.exe'):
                            # Берем первый найденный .exe
                            exe_path = os.path.join(root, file)
                            exe_path = normalize_path(exe_path)
                            if os.path.exists(exe_path):
                                return exe_path
                    # Ограничиваем поиск только корневой папкой для скорости
                    break
    except (WindowsError, FileNotFoundError, OSError):
        pass

    # Пробуем получить из других полей
    try:
        # Некоторые программы хранят путь в поле "Application"
        application = winreg.QueryValueEx(app_key, "Application")[0]
        if application and os.path.exists(application) and application.lower().endswith('.exe'):
            return normalize_path(application)
    except (WindowsError, FileNotFoundError, OSError):
        pass

    return None


def get_program_icon(app_key):
    """
    Извлекает путь к иконке программы из ключа реестра
    """
    icon_path = None

    try:
        # Пробуем получить DisplayIcon
        display_icon = winreg.QueryValueEx(app_key, "DisplayIcon")[0]
        if display_icon:
            # Извлекаем путь из DisplayIcon (иногда там есть запятая с номером ресурса)
            if ',' in display_icon:
                icon_path = display_icon.split(',')[0]
            else:
                icon_path = display_icon

            icon_path = normalize_path(icon_path)

            # Иконка может быть в .exe, .dll, .ico файлах
            if icon_path and os.path.exists(icon_path):
                return icon_path
    except (WindowsError, FileNotFoundError, OSError):
        pass

    # Если не нашли иконку, но есть путь к exe, используем его как иконку
    # (Windows умеет извлекать иконки из exe файлов)
    exe_path = get_program_exe_path(app_key)
    if exe_path and os.path.exists(exe_path):
        return exe_path

    return None


def export_installed_programs(json_output_file=None):
    """
    Записывает информацию об установленных программах в JSON файл
    Каждый элемент содержит только: name, icon, path (путь к .exe)
    """
    print("=" * 60)
    print("ЭКСПОРТ УСТАНОВЛЕННЫХ ПРОГРАММ В JSON")
    print("=" * 60)

    # Получаем путь к папке, где находится этот скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Создаем имя файла с датой, если не указано
    if json_output_file is None:
        json_output_file = f"./config/installed_programs.json"

    # Полный путь к файлу (в папке скрипта)
    full_path = os.path.join(script_dir, json_output_file)

    print(f"Путь к папке скрипта: {script_dir}")
    print(f"Файл будет сохранен: {full_path}")
    print(f"Сканирование реестра Windows...")

    programs = []  # Список для хранения информации о программах
    seen_exe_paths = set()  # Для отслеживания дубликатов по пути к exe

    # Пути в реестре для поиска установленных программ
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hkey, subkey in registry_paths:
        try:
            with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                print(f"  Обработка: {subkey} ({num_subkeys} записей)")

                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as app_key:
                            program_info = {}

                            # Получаем название программы (обязательное поле)
                            try:
                                program_info['name'] = winreg.QueryValueEx(app_key, "DisplayName")[0]
                            except (WindowsError, FileNotFoundError, OSError):
                                continue

                            # Пропускаем пустые названия
                            if not program_info['name']:
                                continue

                            # Получаем путь к исполняемому файлу (обязательное поле)
                            exe_path = get_program_exe_path(app_key)

                            # Если путь к exe не найден - пропускаем программу
                            if not exe_path:
                                continue

                            # Нормализуем путь и проверяем дубликаты
                            normalized_path = normalize_path(exe_path)
                            if normalized_path in seen_exe_paths:
                                continue
                            seen_exe_paths.add(normalized_path)

                            # Добавляем путь к исполняемому файлу
                            program_info['path'] = normalized_path

                            # Получаем путь к иконке (опциональное поле, может быть None)
                            program_info['icon'] = get_program_icon(app_key)

                            # Добавляем программу в список
                            programs.append(program_info)

                    except (WindowsError, OSError):
                        continue
        except WindowsError:
            continue

    # Сортируем программы по названию
    programs.sort(key=lambda x: x['name'].lower())

    # Сохраняем в JSON файл
    print(f"\nСохранение в файл: {full_path}")
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)

    print(f"\nГОТОВО! Найдено программ: {len(programs)}")
    print(f"Файл сохранен: {full_path}")


if __name__ == "__main__":
    try:
        export_installed_programs()

    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback

        traceback.print_exc()
