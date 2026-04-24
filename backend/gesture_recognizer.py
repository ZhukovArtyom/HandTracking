import json
import time
import threading
import numpy as np
import win32api
import win32con
import keyboard
import subprocess

from config_loader import config

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')
CONTROL_HAND = config.get('cursor.control_hand')
SECOND_HAND = "left" if CONTROL_HAND == "right" else "right"

class GestureRecognizer:
    def __init__(self, gestures_file='config/gestures.json'):

        self.gestures_file = gestures_file
        self.gestures = []
        self.active_gestures = {}  # {gesture_id: {'start_time': timestamp, 'hold_activated': False}}
        self.blocked_until_release = False  # Флаг блокировки других жестов
        self.blocking_gesture_id = None  # ID жеста, который блокирует остальные

        self.last_execution_time = {}  # {gesture_id: last_execution_timestamp}
        self.lock = threading.Lock()

        # Загружаем жесты из файла
        self.load_gestures()

    def load_gestures(self):
        """Загружает жесты из JSON файла"""
        try:
            with open(self.gestures_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.gestures = data.get('gestures', [])
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

    def execute_action(self, gesture, current_time):

        gesture_id = gesture['id']

        # Если есть активный блокирующий жест и это не тот же жест
        if self.blocked_until_release and self.blocking_gesture_id != gesture_id:
            return False

        # Проверяем, активен ли уже жест
        if gesture_id not in self.active_gestures:
            # Жест только начался - вызываем on_press
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

            return True
        else:

            return False

    def on_gesture_release(self, gesture_id):

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

    def perform_left_click(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


    def perform_left_click_release(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


    def perform_right_click(self):
       win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)


    def perform_right_click_release(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


    def _perform_action(self, gesture, on_release: bool = False):
        gesture_type = gesture['type']

        if gesture_type == "system":
            action = gesture['on_press'] if not on_release else gesture['on_release']
            if action == 'left_click_press':
                self.perform_left_click()

            elif action == 'left_click_release':
                self.perform_left_click_release()

            elif action == 'right_click_press':
                self.perform_right_click()

            elif action == 'right_click_release':
                self.perform_right_click_release()
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
                    del self.active_gestures[gesture_id]

    def reload_gestures(self):
        """Перезагружает жесты из файла"""
        self.load_gestures()
        with self.lock:
            for gesture_id in list(self.active_gestures.keys()):
                self.on_gesture_release(gesture_id)
            self.active_gestures.clear()
            self.last_execution_time.clear()
            self.blocked_until_release = False
            self.blocking_gesture_id = None