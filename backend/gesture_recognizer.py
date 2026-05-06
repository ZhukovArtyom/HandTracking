import json
import time
import threading
import numpy as np
import win32api
import win32con
import keyboard
import subprocess

from pynput.keyboard import Key, Controller

from config_loader import config

SENSITIVITY_ZONE_PERCENT = config.get('cursor.sensitivity_zone_percent')
CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold') / 100 * SENSITIVITY_ZONE_PERCENT
ACTIVATION_DELAY = config.get('gestures.activation_delay')


CONTROL_HAND = config.get('cursor.control_hand')
SECOND_HAND = "left" if CONTROL_HAND == "right" else "right"


class GestureRecognizer:
    def __init__(self, gestures_file='config/gestures.json'):

        self.gestures_file = gestures_file
        self.gestures = []
        self.active_gestures = {}  # {gesture_id: {'start_time': timestamp, 'hold_activated': False}}
        self.pending_gestures = {}  # {gesture_id: {'timer': timer_object, 'gesture': gesture, 'first_detected': timestamp}}
        self.blocked_until_release = False  # Флаг блокировки других жестов
        self.blocking_gesture_id = None  # ID жеста, который блокирует остальные

        self.last_execution_time = {}  # {gesture_id: last_execution_timestamp}
        self.lock = threading.Lock()

        # Загружаем жесты из файла
        self.load_gestures()

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
        return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2) / 100 * SENSITIVITY_ZONE_PERCENT

    def check_point_group(self, landmarks_dict, point_group):
        """
        Проверяет, что все точки в группе находятся близко друг к другу
        Поддерживает межручные группы (например: left_8, right_8)

        Args:
            landmarks_dict: словарь с точками {'left': [...], 'right': [...]}
            point_group: список индексов точек, может содержать префиксы 'left_' или 'right_'

        Returns:
            bool: True если все точки близко друг к другу
        """
        if not landmarks_dict or len(point_group) < 2:
            return False

        # Получаем координаты всех точек в группе
        points = []
        for point_spec in point_group:
            # Разбираем спецификацию точки
            # Межручная точка: например 'left_8' или 'right_8'
            hand_type, idx = point_spec.split('_')
            hand_type = CONTROL_HAND if hand_type == "main" else SECOND_HAND

            idx = int(idx)
            if hand_type in landmarks_dict and landmarks_dict[hand_type] is not None:
                if idx < len(landmarks_dict[hand_type]):
                    points.append(landmarks_dict[hand_type][idx])
                else:
                    return False
            else:
                return False

        # Проверяем, что максимальное расстояние между любой парой точек меньше порога
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                distance = self.calculate_distance(points[i], points[j])
                if distance > CLICK_DISTANCE_THRESHOLD:
                    return False

        return True

    def check_gesture(self, landmarks_dict, gesture):

        # Если нет групп точек, жест не выполнен
        if not gesture.get('points_groups'):
            return False

        # Проверяем, что все группы точек пересекаются
        for point_group in gesture['points_groups']:
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

    def execute_after_delay(self, gesture, current_time):
        """Выполняет жест после задержки"""
        gesture_id = gesture['id']

        # Проверяем, что жест все еще в ожидании и не был отменен
        if gesture_id in self.pending_gestures:
            # Убираем из pending до выполнения
            del self.pending_gestures[gesture_id]

            # Выполняем действие
            self.active_gestures[gesture_id] = {
                'start_time': current_time,
                'hold_activated': False
            }

            # Устанавливаем блокировку для других жестов
            if not self.blocked_until_release:
                self.blocked_until_release = True
                self.blocking_gesture_id = gesture_id
                print(f"=== Жест {gesture['name']} заблокировал другие жесты ===")

            print(f"Жест активирован: {gesture['name']}")
            self._perform_action(gesture)
            self.last_execution_time[gesture_id] = current_time

    def execute_action(self, gesture, current_time):
        """Запускает таймер для отложенной активации жеста"""
        gesture_id = gesture['id']

        # Если жест уже активен - игнорируем
        if gesture_id in self.active_gestures:
            return False

        # Если есть активный блокирующий жест и это не тот же жест
        if self.blocked_until_release and self.blocking_gesture_id != gesture_id:
            return False

        # Если жест уже в очереди ожидания - просто возвращаемся, не обновляем таймер
        if gesture_id in self.pending_gestures:
            return True

        # Если есть другой отложенный жест - отменяем его и запускаем новый
        if self.pending_gestures:
            print(f"Обнаружен новый жест, отмена предыдущего")
            for pending_id in list(self.pending_gestures.keys()):
                self.cancel_pending_gesture(pending_id)

        # Особый случай: задержка 0 секунд - активируем мгновенно
        if ACTIVATION_DELAY <= 0:
            print(f"Жест {gesture['name']} активирован мгновенно")
            self.active_gestures[gesture_id] = {
                'start_time': current_time,
                'hold_activated': False
            }

            if not self.blocked_until_release:
                self.blocked_until_release = True
                self.blocking_gesture_id = gesture_id
                print(f"=== Жест {gesture['name']} заблокировал другие жесты ===")

            print(f"Жест активирован: {gesture['name']}")
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

        print(f"Жест {gesture['name']} обнаружен, активация через {ACTIVATION_DELAY} секунд")
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
                    print(f"Жест деактивирован: {gesture['name']}")
                    self._perform_action(gesture, True)

                    # Снимаем блокировку, если это был блокирующий жест
                    if self.blocking_gesture_id == gesture_id:
                        self.blocked_until_release = False
                        self.blocking_gesture_id = None
                        print(f"=== Блокировка жестов снята ===")
                    break

            del self.active_gestures[gesture_id]


    def _perform_action(self, gesture, on_release: bool = False):
        gesture_type = gesture['type']

        if gesture_type == "system":
            action = gesture['on_press'] if not on_release else gesture['on_release']
            if action == 'left_click_press':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

            elif action == 'left_click_release':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            elif action == 'right_click_press':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)

            elif action == 'right_click_release':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

            elif action == 'wheel_up':

                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 30, 0)
                time.sleep(0.03)
                self.on_gesture_release(gesture['id'])

            elif action == 'wheel_down':

                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -30, 0)
                time.sleep(0.03)
                self.on_gesture_release(gesture['id'])

            elif action == 'volume_up':
                keyboard.press('volume up')
                time.sleep(0.03)
                self.on_gesture_release(gesture['id'])


            elif action == 'volume_down':
                keyboard.press('volume down')
                time.sleep(0.03)
                self.on_gesture_release(gesture['id'])

            else:
                print(f"Неизвестное действие: {action}")

        elif gesture_type == "keyboard":
            if not on_release:
                action = gesture['on_press']
                keyboard.send(action)
            else:
                return

        elif gesture_type == "program":
            if not on_release:
                action = gesture['on_press']
                subprocess.Popen([action])
            else:
                return

        else:
            print(f"Тип действия не обозначен")

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

                if self.blocked_until_release:
                    self.blocked_until_release = False
                    self.blocking_gesture_id = None

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
            # Отменяем все отложенные жесты
            for gesture_id in list(self.pending_gestures.keys()):
                self.cancel_pending_gesture(gesture_id)

            for gesture_id in list(self.active_gestures.keys()):
                self.on_gesture_release(gesture_id)
            self.active_gestures.clear()
            self.last_execution_time.clear()
            self.blocked_until_release = False
            self.blocking_gesture_id = None