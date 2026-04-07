import json
import time
import threading
import numpy as np
import win32api
import win32con

from config_loader import config

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')
HOLD_THRESHOLD = config.get('gestures.hold_threshold')


class GestureRecognizer:
    def __init__(self, gestures_file='config/gestures.json'):
        """
        Инициализация распознавателя жестов

        Args:
            gestures_file: путь к JSON файлу с описанием жестов
        """
        self.gestures_file = gestures_file
        self.gestures = []
        self.active_gestures = {}  # {gesture_id: {'start_time': timestamp, 'hold_activated': False}}
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

    def check_point_group(self, landmarks, point_group):
        """
        Проверяет, что все точки в группе находятся близко друг к другу

        Args:
            landmarks: список точек руки
            point_group: список индексов точек для проверки

        Returns:
            bool: True если все точки близко друг к другу
        """
        if not landmarks or len(point_group) < 2:
            return False

        # Получаем координаты всех точек в группе
        points = []
        for idx in point_group:
            if idx < len(landmarks):
                points.append(landmarks[idx])
            else:
                return False

        # Проверяем, что максимальное расстояние между любой парой точек меньше порога
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
        """
        Выполняет действие жеста на on_press и on_release

        Args:
            gesture: словарь с описанием жеста
            current_time: текущее время
            target_pos: целевая позиция (x, y)
        """
        gesture_id = gesture['id']
        hold_enabled = gesture.get('hold_enabled', False)
        cooldown = gesture.get('cooldown', 0)

        # Проверяем кулдаун для on_press
        if gesture_id in self.last_execution_time:
            if current_time - self.last_execution_time[gesture_id] < cooldown:
                return False

        # Проверяем, активен ли уже жест
        if gesture_id not in self.active_gestures:
            # Жест только начался - вызываем on_press
            self.active_gestures[gesture_id] = {
                'start_time': current_time,
                'hold_activated': False
            }

            print(f"Жест активирован: {gesture['name']}")
            self._perform_action(gesture['on_press'], target_pos, gesture)
            self.last_execution_time[gesture_id] = current_time

            return True
        else:
            # Жест уже активен
            gesture_data = self.active_gestures[gesture_id]

            # Если включен режим удержания и еще не активирован
            if hold_enabled and not gesture_data['hold_activated']:
                hold_duration = current_time - gesture_data['start_time']
                if hold_duration >= HOLD_THRESHOLD:
                    # Достигнут порог удержания - вызываем on_press повторно
                    gesture_data['hold_activated'] = True
                    if 'on_press' in gesture:
                        print(f"Жест удержан: {gesture['name']} ({(hold_duration * 1000):.0f}ms)")
                        self._perform_action(gesture['on_press'], target_pos, gesture)
                        self.last_execution_time[gesture_id] = current_time
                    return True

            return False

    def on_gesture_release(self, gesture_id, target_pos):
        """
        Вызывается когда жест перестает распознаваться

        Args:
            gesture_id: идентификатор жеста
            target_pos: целевая позиция (x, y)
        """
        # Находим жест по ID
        for gesture in self.gestures:
            if gesture['id'] == gesture_id:

                print(f"Жест деактивирован: {gesture['name']}")
                self._perform_action(gesture['on_release'], target_pos, gesture)
                break

    def perform_left_click(self, x, y):



        # Левый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

        print(f"Левый клик! В точке: ({x:.0f}, {y:.0f})")

    def perform_left_click_release(self, x, y):

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print(f"Левый клик отпущен! В точке: ({x:.0f}, {y:.0f})")

    def perform_right_click(self, x, y):

        # Правый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)

        print(f"Правый клик! В точке: ({x:.0f}, {y:.0f})")

    def perform_right_click_release(self, x, y):

        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        print(f"правый клик отпущен! В точке: ({x:.0f}, {y:.0f})")

    def _perform_action(self, action, target_pos, gesture):
        """
        Выполняет действие жеста

        Args:
            action: тип действия (str)
            target_pos: целевая позиция (x, y)
            gesture: словарь с описанием жеста
        """
        if action == 'left_click_press':
            if target_pos:
                self.perform_left_click(target_pos[0], target_pos[1])
            else:
                print(f"Ошибка: нет позиции для левого клика")

        elif action == 'left_click_relese':
            if target_pos:
                self.perform_left_click_release(target_pos[0], target_pos[1])
            else:
                print(f"Ошибка: нет позиции для правого клика")

        elif action == 'right_click_press':
            if target_pos:
                self.perform_right_click(target_pos[0], target_pos[1])
            else:
                print(f"Ошибка: нет позиции для правого клика")

        elif action == 'right_click_release':
            if target_pos:
                self.perform_right_click_release(target_pos[0], target_pos[1])
            else:
                print(f"Ошибка: нет позиции для правого клика")

        else:
            print(f"Неизвестное действие: {action}")

    def recognize_and_execute(self, landmarks, target_pos):
        """
        Распознает жест и выполняет соответствующее действие

        Args:
            landmarks: список точек руки
            target_pos: целевая позиция (x, y)
        """
        if not landmarks:
            # Если нет руки, сбрасываем все активные жесты
            with self.lock:
                # Вызываем on_release для всех активных жестов
                for gesture_id in list(self.active_gestures.keys()):
                    self.on_gesture_release(gesture_id, target_pos)
                self.active_gestures.clear()
            return

        current_time = time.time()

        with self.lock:
            active_gesture_ids = set()

            # Проверяем все загруженные жесты
            for gesture in self.gestures:
                if self.check_gesture(landmarks, gesture):
                    active_gesture_ids.add(gesture['id'])
                    # Жест распознан
                    self.execute_action(gesture, current_time, target_pos)

            # Проверяем, какие жесты перестали быть активными
            for gesture_id in list(self.active_gestures.keys()):
                if gesture_id not in active_gesture_ids:
                    # Жест больше не распознается - вызываем on_release
                    self.on_gesture_release(gesture_id, target_pos)
                    del self.active_gestures[gesture_id]

    def reload_gestures(self):
        """Перезагружает жесты из файла"""
        self.load_gestures()
        with self.lock:
            # Вызываем on_release для всех активных жестов перед очисткой
            for gesture_id in list(self.active_gestures.keys()):
                self.on_gesture_release(gesture_id, None)
            self.active_gestures.clear()
            self.last_execution_time.clear()