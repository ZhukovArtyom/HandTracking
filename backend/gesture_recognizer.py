import json
import time
import threading
from collections import defaultdict
import numpy as np


class GestureRecognizer:
    def __init__(self, gestures_file='gestures.json'):
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
        """
        Вычисляет расстояние между двумя точками

        Args:
            point1: точка с атрибутами x, y
            point2: точка с атрибутами x, y

        Returns:
            float: расстояние между точками
        """
        return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

    def check_point_group(self, landmarks, point_group, distance_threshold=0.05):
        """
        Проверяет, все ли точки в группе пересекаются (находятся близко друг к другу)

        Args:
            landmarks: список точек руки от MediaPipe
            point_group: список индексов точек (например [4, 8] или [4, 3, 2])
            distance_threshold: порог расстояния для определения пересечения

        Returns:
            bool: True если все точки близки друг к другу
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

        # Проверяем, что все точки находятся близко друг к другу
        # Для этого проверяем, что максимальное расстояние между любой парой точек меньше порога
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                distance = self.calculate_distance(points[i], points[j])
                if distance > distance_threshold:
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

    def execute_action(self, gesture, current_time, cursor_controller, target_pos):
        """
        Выполняет действие, привязанное к жесту

        Args:
            gesture: словарь с описанием жеста
            current_time: текущее время
            cursor_controller: экземпляр AdvancedCursorController
            target_pos: целевая позиция курсора (x, y)
        """
        action = gesture.get('action')
        cooldown = gesture.get('cooldown', 0)
        hold_enabled = gesture.get('hold_enabled', False)
        hold_threshold = gesture.get('hold_threshold', 0.3)

        gesture_id = gesture['id']

        # Проверяем кулдаун
        if gesture_id in self.last_execution_time:
            if current_time - self.last_execution_time[gesture_id] < cooldown:
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
                    if hold_duration >= hold_threshold:
                        # Удержание достигло порога - активируем действие
                        gesture_data['activated'] = True
                        self._perform_action(action, cursor_controller, target_pos, gesture)
                        self.last_execution_time[gesture_id] = current_time
                        return True
                return False
        else:
            # Без удержания - выполняем сразу
            self._perform_action(action, cursor_controller, target_pos, gesture)
            self.last_execution_time[gesture_id] = current_time
            return True

    def _perform_action(self, action, cursor_controller, target_pos, gesture):
        """
        Выполняет конкретное действие

        Args:
            action: строка с названием действия
            cursor_controller: экземпляр AdvancedCursorController
            target_pos: целевая позиция курсора
            gesture: словарь с описанием жеста (для параметров)
        """
        params = gesture.get('params', {})

        if action == 'left_click':
            print(f"Выполняется левый клик (жест: {gesture['name']})")
            if target_pos:
                cursor_controller.perform_left_click(target_pos[0], target_pos[1])

        elif action == 'right_click':
            print(f"Выполняется правый клик (жест: {gesture['name']})")
            if target_pos:
                cursor_controller.perform_right_click(target_pos[0], target_pos[1])

        elif action == 'drag_drop':
            print(f"Выполняется drag & drop (жест: {gesture['name']})")
            # Здесь можно реализовать логику drag & drop
            # В текущей реализации она уже есть в основном классе
            pass

        elif action == 'double_click':
            print(f"Выполняется двойной клик (жест: {gesture['name']})")
            if target_pos:
                cursor_controller.perform_left_click(target_pos[0], target_pos[1])
                time.sleep(0.1)
                cursor_controller.perform_left_click(target_pos[0], target_pos[1])

        elif action == 'scroll_up':
            print(f"Выполняется скролл вверх (жест: {gesture['name']})")
            # Реализация скролла
            import win32con
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)

        elif action == 'scroll_down':
            print(f"Выполняется скролл вниз (жест: {gesture['name']})")
            import win32con
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)

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

    def recognize_and_execute(self, landmarks, cursor_controller, target_pos):
        """
        Основной метод: распознает жест и выполняет действие

        Args:
            landmarks: список точек руки
            cursor_controller: экземпляр AdvancedCursorController
            target_pos: целевая позиция курсора
        """
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
                    self.execute_action(gesture, current_time, cursor_controller, target_pos)
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