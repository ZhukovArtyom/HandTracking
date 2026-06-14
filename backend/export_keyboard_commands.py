import os

import json




# Базовые клавиши
BASIC_KEYS = [
    # Буквы
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',

    # Цифры
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',

    # Функциональные клавиши
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f20', 'f21', 'f22', 'f23', 'f24',

    # Специальные клавиши
    'enter', 'tab', 'space', 'backspace', 'delete', 'insert', 'home', 'end',
    'page up', 'page down', 'pause', 'caps lock', 'scroll lock', 'num lock',
    'print screen', 'menu',

    # Стрелки
    'up', 'down', 'left', 'right',

    # Модификаторы
    'shift', 'ctrl', 'alt', 'windows', 'cmd',

    # Символы
    '`', '-', '=', '[', ']', '\\', ';', ',', '.', '/',
    '~', '_', '+', '{', '}', '|', ':', '"', '<', '>', '?',

    # Numpad
    'num 0', 'num 1', 'num 2', 'num 3', 'num 4', 'num 5',
    'num 6', 'num 7', 'num 8', 'num 9',
    'num lock', 'num /', 'num *', 'num -', 'num +', 'num enter', 'num .',
]

# Сочетания с Ctrl
CTRL_COMBINATIONS = [
    f'ctrl+{key}' for key in BASIC_KEYS
    if len(key) == 1 and key.isalpha()  # только буквы
]

# Сочетания с Alt
ALT_COMBINATIONS = [
    f'alt+{key}' for key in BASIC_KEYS
    if len(key) == 1 and (key.isalpha() or key.isdigit())
]

# Сочетания с Shift
SHIFT_COMBINATIONS = [
    f'shift+{key}' for key in BASIC_KEYS
    if len(key) == 1 and (key.isalpha() or key.isdigit())
]

# Сочетания с Win/Cmd
WIN_COMBINATIONS = [
    f'windows+{key}' for key in ['d', 'e', 'r', '1', '2', '3', '4', '5', 'pause']
]

# Сочетания с Ctrl + Shift
CTRL_SHIFT_COMBINATIONS = [
    f'ctrl+shift+{key}' for key in BASIC_KEYS
    if len(key) == 1 and key.isalpha()
]

# Сочетания с Alt + Shift
ALT_SHIFT_COMBINATIONS = [
    f'alt+shift+{key}' for key in BASIC_KEYS
    if len(key) == 1 and (key.isalpha() or key.isdigit())
]

# Сочетания с Ctrl + Alt
CTRL_ALT_COMBINATIONS = [
    f'ctrl+alt+{key}' for key in BASIC_KEYS
    if len(key) == 1 and key.isalpha()
]

# Популярные сочетания
POPULAR_COMBINATIONS = [

    'alt+f4', 'alt+tab', 'alt+space', 'alt+enter',
    'ctrl+shift+esc', 'ctrl+alt+del', 'windows+r',
    'windows+e', 'windows+d', 'windows+tab',
]




def export_keyboard_commands(json_output_file=None):
    # Экспортирует все возможные клавиши и сочетания клавиш в JSON файл

    print("=" * 60)
    print("ЭКСПОРТ КЛАВИАРНЫХ КОМАНД В JSON")
    print("=" * 60)

    # Получаем путь к папке, где находится этот скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Создаем имя файла с датой, если не указано
    if json_output_file is None:
        json_output_file = "./config/keyboard_commands.json"

    # Полный путь к файлу
    full_path = os.path.join(script_dir, json_output_file)

    print(f"Путь к папке скрипта: {script_dir}")
    print(f"Файл будет сохранен: {full_path}")
    print(f"Генерация списка клавиш...")


    all_commands = []

    # Добавляем все категории
    all_commands.extend(BASIC_KEYS)
    all_commands.extend(CTRL_COMBINATIONS)
    all_commands.extend(ALT_COMBINATIONS)
    all_commands.extend(SHIFT_COMBINATIONS)
    all_commands.extend(WIN_COMBINATIONS)
    all_commands.extend(CTRL_SHIFT_COMBINATIONS)
    all_commands.extend(ALT_SHIFT_COMBINATIONS)
    all_commands.extend(CTRL_ALT_COMBINATIONS)
    all_commands.extend(POPULAR_COMBINATIONS)






    # Сохраняем в JSON файл
    print(f"\nСохранение в файл: {full_path}")
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(all_commands, f, ensure_ascii=False, indent=2)



    print(f"Файл сохранен: {full_path}")





if __name__ == "__main__":
    try:
        # Экспорт полной версии
        export_keyboard_commands()
        print("\n" + "-" * 60)



    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback

        traceback.print_exc()
