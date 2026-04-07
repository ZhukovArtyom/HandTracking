import json
import time
import threading
from collections import defaultdict
import numpy as np
import win32api
import win32con

from config_loader import config

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')
CLICK_COOLDOWN = config.get('gestures.click_cooldown')
HOLD_THRESHOLD = config.get('gestures.hold_threshold')
DRAG_LOSS_TIMEOUT = config.get('gestures.drag_loss_timeout')

class GestureRecognizer:
    def __init__(self, gestures_file='config/gestures.json'):
        """
        Инициализация распознавателя жестов

        Args:
            gestures_file: путь к JSON файлу с описанием жестов
        """
        self.gestures_file = gestures_file
        self.gestures = []
        self.active_gestures = {}  # {gesture_id: {'start_time': timestamp, 'activated': False}}
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
                for gesture in self.gestures:
                    print(f"  - {gesture['name']} (id: {gesture['id']})")
        except FileNotFoundError:
            print(f"Файл {self.gestures_file} не найден!")
            self.gestures = []
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            self.gestures = []

    def calculate_distance(self, point1, point2):

        return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

    def check_point_group(self, landmarks, point_group):

        if not landmarks or len(point_group) < 2:
            return False

        # Получаем координаты всех точек в группе
        points = []
        for idx in point_group:
            if idx < len(landmarks):
                points.append(landmarks[idx])
            else:
                return False

        # Проверяем, что все точки находятся близко друг к другу
        # Для этого проверяем, что максимальное расстояние между любой парой точек меньше порога
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                distance = self.calculate_distance(points[i], points[j])
                if distance > CLICK_DISTANCE_THRESHOLD:
                    return False

        return True

    def check_gesture(self, landmarks, gesture):
        """
        Проверяет, выполнен ли конкретный жест

        Args:
            landmarks: список точек руки
            gesture: словарь с описанием жеста

        Returns:
            bool: True если жест выполнен
        """
        # Если нет групп точек, жест не выполнен
        if not gesture.get('points_groups'):
            return False

        # Проверяем, что все группы точек пересекаются
        for point_group in gesture['points_groups']:
            if not self.check_point_group(landmarks, point_group):
                return False

        return True

    def execute_action(self, gesture, current_time, target_pos):

        action = gesture.get('action')
        hold_enabled = gesture.get('hold_enabled', False)

        gesture_id = gesture['id']

        # Проверяем кулдаун
        if gesture_id in self.last_execution_time:
            if current_time - self.last_execution_time[gesture_id] < CLICK_COOLDOWN:
                return False

        # Обработка удержания для жестов с поддержкой hold
        if hold_enabled:
            if gesture_id not in self.active_gestures:
                # Жест только начался
                self.active_gestures[gesture_id] = {
                    'start_time': current_time,
                    'activated': False
                }
                return False
            else:
                # Жест уже активен
                gesture_data = self.active_gestures[gesture_id]
                hold_duration = current_time - gesture_data['start_time']

                if not gesture_data['activated']:
                    if hold_duration >= HOLD_THRESHOLD:
                        # Удержание достигло порога - активируем действие
                        gesture_data['activated'] = True
                        self._perform_action(action, target_pos, gesture)
                        self.last_execution_time[gesture_id] = current_time
                        return True
                return False
        else:
            # Без удержания - выполняем сразу
            self._perform_action(action, target_pos, gesture)
            self.last_execution_time[gesture_id] = current_time
            return True

    def perform_left_click(self, x, y):
        """Выполняет левый клик"""
        # Устанавливаем курсор в позицию клика
        win32api.SetCursorPos((int(x), int(y)))

        # Левый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print(f"Левый клик! В точке: ({x}, {y})")

    def perform_right_click(self, x, y):
        """Выполняет правый клик"""
        # Устанавливаем курсор в позицию клика
        win32api.SetCursorPos((int(x), int(y)))

        # Правый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        print(f"Правый клик! В точке: ({x}, {y})")

    def start_drag(self, x, y):
        """Начинает перетаскивание"""
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        print(f"Начало перетаскивания в точке: ({x}, {y})")

    def end_drag(self, x, y):
        """Завершает перетаскивание"""
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print(f"Завершение перетаскивания в точке: ({x}, {y})")

    def _perform_action(self, action, target_pos, gesture):

        params = gesture.get('params', {})

        if action == 'left_click':
            print(f"Выполняется левый клик (жест: {gesture['name']})")
            if target_pos:
                self.perform_left_click(target_pos[0], target_pos[1])

        elif action == 'right_click':
            print(f"Выполняется правый клик (жест: {gesture['name']})")
            if target_pos:
                self.perform_right_click(target_pos[0], target_pos[1])

        elif action == 'drag_drop':
            print(f"Выполняется drag & drop (жест: {gesture['name']})")


        else:
            print(f"Неизвестное действие: {action}")

    def reset_hold(self, gesture_id):
        """
        Сбрасывает состояние удержания для жеста

        Args:
            gesture_id: идентификатор жеста
        """
        if gesture_id in self.active_gestures:
            del self.active_gestures[gesture_id]

    def recognize_and_execute(self, landmarks, target_pos):

        if not landmarks:
            # Если нет руки, сбрасываем все активные удержания
            with self.lock:
                self.active_gestures.clear()
            return

        current_time = time.time()

        with self.lock:
            # Проверяем все загруженные жесты
            for gesture in self.gestures:
                if self.check_gesture(landmarks, gesture):
                    # Жест распознан
                    self.execute_action(gesture, current_time, target_pos)
                else:
                    # Жест не выполнен - сбрасываем состояние удержания если оно было
                    if gesture['id'] in self.active_gestures:
                        del self.active_gestures[gesture['id']]

    def reload_gestures(self):
        """Перезагружает жесты из файла"""
        self.load_gestures()
        with self.lock:
            self.active_gestures.clear()
            self.last_execution_time.clear()