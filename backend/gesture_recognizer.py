import json
import time
import threading
import os
import numpy as np
import sys

# Для кликов и колёсика мыши
import ctypes

import keyboard
import subprocess

# Для режима разработки
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Для собранного приложения добавляем resources/backend
if getattr(sys, 'frozen', False):
    resources_dir = os.path.join(os.path.dirname(sys.executable), 'resources', 'backend')
    if resources_dir not in sys.path:
        sys.path.insert(0, resources_dir)

from config_loader import config

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')
ACTIVATION_DELAY = config.get('gestures.activation_delay')


CONTROL_HAND = config.get('cursor.control_hand')
SECOND_HAND = "left" if CONTROL_HAND == "right" else "right"


class GestureRecognizer:
    def __init__(self, gestures_file='config/gestures.json'):

        self.razengan = False

        self.gestures_file = gestures_file
        self.gestures = []
        self.active_gestures = {}  # {gesture_id: {'start_time': timestamp, 'hold_activated': False}}
        self.pending_gestures = {}  # {gesture_id: {'timer': timer_object, 'gesture': gesture, 'first_detected': timestamp}}
        self.program_executed = set()  # {gesture_id: bool} - для отслеживания уже открытых программ


        self.global_blocked = False  # Глобальная блокировка для двуручных жестов
        self.global_blocking_gesture_id = None

        # Блокировка по рукам (для одноручных жестов)
        self.hand_blocked = {'main': False, 'second': False}
        self.hand_blocking_gesture = {'main': None, 'second': None}


        self.last_execution_time = {}  # {gesture_id: last_execution_timestamp}
        self.lock = threading.Lock()

        # Загружаем жесты из файла
        self.load_gestures()


    def get_gesture_hand_type(self, gesture):

        has_main = False
        has_second = False

        # Определяем, какая рука используется
        for point_group in gesture['points_groups']:
            for point_spec in point_group:
                if point_spec.startswith('main'):
                    has_main = True
                if point_spec.startswith('second'):
                    has_second = True

        if has_main and has_second:
            return 'both'
        elif has_main and not has_second:
            return 'main'
        else:
            return 'second'

    def update_control_hand(self, new_control_hand):
        """Обновляет контрольную руку для жестов"""
        global CONTROL_HAND, SECOND_HAND
        CONTROL_HAND = new_control_hand
        SECOND_HAND = "left" if CONTROL_HAND == "right" else "right"
        print(f"Gesture recognizer: control hand updated to {CONTROL_HAND}")

    def update_activation_delay(self, new_delay):
        """Обновляет задержку активации жестов"""
        global ACTIVATION_DELAY
        ACTIVATION_DELAY = new_delay
        print(f"Activation delay updated to {ACTIVATION_DELAY}s")

    def update_click_threshold(self, new_threshold):
        """Обновляет порог расстояния для клика"""
        global CLICK_DISTANCE_THRESHOLD
        CLICK_DISTANCE_THRESHOLD = new_threshold
        print(f"Click threshold updated to {CLICK_DISTANCE_THRESHOLD}")

    def load_gestures(self):
        """Загружает жесты из JSON файла"""
        try:
            with open(self.gestures_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_gestures = data.get('gestures', [])
                # Фильтруем: оставляем только те, у которых enabled == "true"
                self.gestures = [g for g in all_gestures if g.get('enabled') == True]

                print(f"Загружено {len(self.gestures)} жестов:")

        except FileNotFoundError:
            print(f"Файл {self.gestures_file} не найден!")
            self.gestures = []
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            self.gestures = []

    def calculate_distance(self, point1, point2):
        """Вычисляет расстояние между двумя точками"""
        return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

    def check_point_group(self, landmarks_dict, point_group):
        # проверяем пересечения точек


        # Получаем координаты первой точки
        hand_type1, idx1 = point_group[0].split('_')
        hand_type1 = CONTROL_HAND if hand_type1 == "main" else SECOND_HAND
        idx1 = int(idx1)

        # Получаем координаты второй точки
        hand_type2, idx2 = point_group[1].split('_')
        hand_type2 = CONTROL_HAND if hand_type2 == "main" else SECOND_HAND
        idx2 = int(idx2)

        # Проверяем наличие рук и индексов
        if hand_type1 not in landmarks_dict or landmarks_dict[hand_type1] is None:
            return False
        if hand_type2 not in landmarks_dict or landmarks_dict[hand_type2] is None:
            return False

        if idx1 >= len(landmarks_dict[hand_type1]) or idx2 >= len(landmarks_dict[hand_type2]):
            return False

        # Получаем точки
        point1 = landmarks_dict[hand_type1][idx1]
        point2 = landmarks_dict[hand_type2][idx2]

        # Вычисляем расстояние между точками
        distance = self.calculate_distance(point1, point2)

        return distance <= CLICK_DISTANCE_THRESHOLD

    def check_gesture(self, landmarks_dict, gesture):
        points_groups = gesture.get('points_groups')
        # Если нет групп точек, жест не выполнен
        if not points_groups:
            return False

        # Проверяем, что все группы точек пересекаются
        for point_group in points_groups:
            if not self.check_point_group(landmarks_dict, point_group):
                return False

        return True

    def cancel_pending_gesture(self, gesture_id):
        """Отменяет отложенный жест"""
        if gesture_id in self.pending_gestures:
            pending = self.pending_gestures[gesture_id]
            if pending['timer'] is not None:
                pending['timer'].cancel()
            del self.pending_gestures[gesture_id]
            print(f"Жест отменен до активации")

    def can_execute_gesture(self, gesture):
        """Проверяет, можно ли выполнить жест с учётом текущих блокировок"""
        gesture_hand = self.get_gesture_hand_type(gesture)

        if self.global_blocked:
            return False

        if gesture_hand == 'both':
            return not self.hand_blocked['main'] and not self.hand_blocked['second']

        # Если жест одноручный - проверяем блокировку только на этой руке
        return not self.hand_blocked[gesture_hand]

    def block_gesture(self, gesture):

        gesture_hand = self.get_gesture_hand_type(gesture)

        if gesture_hand == 'both':
            self.global_blocked = True
            self.global_blocking_gesture_id = gesture['id']
        else:
            self.hand_blocked[gesture_hand] = True
            self.hand_blocking_gesture[gesture_hand] = gesture['id']

    def unblock_gesture(self, gesture):

        gesture_hand = self.get_gesture_hand_type(gesture)

        if gesture_hand == 'both':
            self.global_blocked = False
            self.global_blocking_gesture_id = None

        else:
            self.hand_blocked[gesture_hand] = False
            self.hand_blocking_gesture[gesture_hand] = None



    def execute_after_delay(self, gesture, current_time):
        """Выполняет жест после задержки"""
        gesture_id = gesture['id']

        # Проверяем, что жест все еще в ожидании и не был отменен
        if gesture_id in self.pending_gestures:
            # Убираем из pending до выполнения
            del self.pending_gestures[gesture_id]

            if not self.can_execute_gesture(gesture):
                return

            # Выполняем действие
            self.active_gestures[gesture_id] = {
                'start_time': current_time,
                'hold_activated': False,
                'hand_type': self.get_gesture_hand_type(gesture)
            }

            self.block_gesture(gesture)

            print(f"Жест активирован: {gesture['name']}")
            self._perform_action(gesture)
            self.last_execution_time[gesture_id] = current_time

    def execute_action(self, gesture, current_time):
        """Запускает таймер для отложенной активации жеста"""
        gesture_id = gesture['id']


        # Если жест уже активен - игнорируем
        if gesture_id in self.active_gestures:
            return False

        # Можем ли выполнить жест?
        if not self.can_execute_gesture(gesture):
            return False

        # Если жест уже в очереди ожидания - просто возвращаемся, не обновляем таймер
        if gesture_id in self.pending_gestures:
            return True

        # Если есть другой отложенный жест - отменяем его и запускаем новый
        if self.pending_gestures:
            current_points = len(gesture.get('points_groups', []))

            # Получаем максимальное количество точек среди pending жестов
            max_pending_points = max(
                len(pending_data['gesture'].get('points_groups', []))
                for pending_data in self.pending_gestures.values()
            )

            # Если текущий жест не сложнее существующего - не отменяем
            if current_points <= max_pending_points:
                return False

            # Если текущий жест сложнее - отменяем все существующие
            for pending_id in list(self.pending_gestures.keys()):
                self.cancel_pending_gesture(pending_id)

        # Особый случай: задержка 0 секунд - активируем мгновенно
        if ACTIVATION_DELAY <= 0:
            print(f"Жест {gesture['name']} активирован мгновенно")
            self.active_gestures[gesture_id] = {
                'start_time': current_time,
                'hold_activated': False,
                'hand_type': self.get_gesture_hand_type(gesture)
            }

            self.block_gesture(gesture)

            self._perform_action(gesture)
            self.last_execution_time[gesture_id] = current_time
            return True

        # Создаем новый отложенный жест с таймером
        timer = threading.Timer(ACTIVATION_DELAY, self.execute_after_delay, [gesture, current_time])
        timer.daemon = True
        timer.start()

        self.pending_gestures[gesture_id] = {
            'timer': timer,
            'gesture': gesture,
            'first_detected': current_time
        }


        return True

    def on_gesture_release(self, gesture_id):
        """Вызывается когда жест перестает распознаваться"""

        # Если жест был в ожидании - отменяем таймер
        if gesture_id in self.pending_gestures:
            self.cancel_pending_gesture(gesture_id)
            return

        # Если жест был активен - выполняем on_release
        if gesture_id in self.active_gestures:
            # Находим жест по ID
            for gesture in self.gestures:
                if gesture['id'] == gesture_id:

                    self._perform_action(gesture, True)
                    self.unblock_gesture(gesture)
                    break

            del self.active_gestures[gesture_id]


    def _perform_action(self, gesture, on_release: bool = False):
        gesture_type = gesture['type']

        if gesture_type == "system":
            action = gesture['on_press'] if not on_release else gesture['on_release']
            if action == 'left_click_press':
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)


            elif action == 'left_click_release':
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)


            elif action == 'double_click':
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

            elif action == 'right_click_press':
                ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)

            elif action == 'right_click_release':
                ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)

            elif action == 'wheel_press':
                ctypes.windll.user32.mouse_event(0x0020, 0, 0, 0, 0)

            elif action == 'wheel_release':
                ctypes.windll.user32.mouse_event(0x0040, 0, 0, 0, 0)

            elif action == 'wheel_up':
                self.hold_action(gesture['id'], action)

            elif action == 'wheel_down':
                self.hold_action(gesture['id'], action)

            elif action == 'volume_up':
                self.hold_action(gesture['id'], action)

            elif action == 'volume_down':
                self.hold_action(gesture['id'], action)

            else:
                print(f"Неизвестное действие: {action}")

        elif gesture_type == "keyboard":
            action = gesture['on_press'] if not on_release else gesture['on_release']
            if not on_release:
                keyboard.press(action)
            else:
                keyboard.release(action)

        elif gesture_type == "program":
            if not on_release:
                if gesture['id'] not in self.program_executed:
                    path = gesture['on_press']
                    if path.startswith('C:'):
                        os.startfile(path)
                    else:
                        subprocess.run(f'explorer.exe shell:AppsFolder\\{path}', shell=True)

                    self.program_executed.add(gesture['id'])
            else:
                if gesture['id'] in self.program_executed:
                    self.program_executed.discard(gesture['id'])
                return

        elif gesture_type == "naruto":
            self.razengan=True

        else:
            print(f"Тип действия не обозначен")


    def hold_action(self, gesture_id, action):
        def repeat():

            while gesture_id in self.active_gestures:
                # Выполняем действие
                if action == 'volume_up':
                    keyboard.press('volume up')
                elif action == 'volume_down':
                    keyboard.press('volume down')
                elif action == 'wheel_up':
                    ctypes.windll.user32.mouse_event(0x0800, 0, 0, 30, 0)
                elif action == 'wheel_down':
                    ctypes.windll.user32.mouse_event(0x0800, 0, 0, -30, 0)


                time.sleep(0.03)

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=repeat, daemon=True)
        thread.start()


    def is_razengan(self):
        return self.razengan

    def recognize_and_execute(self, landmarks_dict):
        # Проверяем, есть ли хоть какие-то точки
        has_any_hand = False
        for hand_type in ['left', 'right']:
            if hand_type in landmarks_dict and landmarks_dict[hand_type] is not None:
                has_any_hand = True
                break

        if not has_any_hand:
            # Если нет рук, сбрасываем все активные жесты
            with self.lock:
                # Отменяем все отложенные жесты
                for gesture_id in list(self.pending_gestures.keys()):
                    self.cancel_pending_gesture(gesture_id)

                for gesture_id in list(self.active_gestures.keys()):
                    self.on_gesture_release(gesture_id)

                self.active_gestures.clear()
                self.global_blocked = False
                self.global_blocking_gesture_id = None
                self.hand_blocked = {'main': False, 'second': False}
                self.hand_blocking_gesture = {'main': None, 'second': None}
            return

        current_time = time.time()

        with self.lock:
            active_gesture_ids = set()

            # Проверяем все загруженные жесты
            for gesture in self.gestures:
                if self.check_gesture(landmarks_dict, gesture):
                    active_gesture_ids.add(gesture['id'])
                    self.execute_action(gesture, current_time)


            # Проверяем, какие жесты перестали быть активными
            for gesture_id in list(self.active_gestures.keys()):
                if gesture_id not in active_gesture_ids:
                    self.on_gesture_release(gesture_id)

            # Проверяем отложенные жесты - если жест больше не активен, отменяем
            for gesture_id in list(self.pending_gestures.keys()):
                if gesture_id not in active_gesture_ids:
                    self.cancel_pending_gesture(gesture_id)

    def reload_gestures(self):
        """Перезагружает жесты из файла"""
        self.load_gestures()
        with self.lock:
            for gesture_id in list(self.pending_gestures.keys()):
                self.cancel_pending_gesture(gesture_id)
            for gesture_id in list(self.active_gestures.keys()):
                self.on_gesture_release(gesture_id)
            self.active_gestures.clear()
            self.last_execution_time.clear()
            self.global_blocked = False
            self.global_blocking_gesture_id = None
            self.hand_blocked = {'main': False, 'second': False}
            self.hand_blocking_gesture = {'main': None, 'second': None}