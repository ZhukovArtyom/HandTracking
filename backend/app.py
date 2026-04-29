import cv2
import mediapipe as mp
import time
import numpy as np
import threading
import pyautogui
import psutil
import os

import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Импорты для управления курсором (Windows) ---
import win32api
import win32con

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config_loader import config
from gesture_recognizer import GestureRecognizer

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = config.get('camera.width')
CAMERA_HEIGHT = config.get('camera.height')
MODEL_PATH = config.get('model.path')

SENSITIVITY_ZONE_PERCENT = config.get('cursor.sensitivity_zone_percent')
SENSITIVITY_ZONE_X = config.get('cursor.sensitivity_zone_X')
SENSITIVITY_ZONE_Y = config.get('cursor.sensitivity_zone_Y')

PADDING = config.get('cursor.padding')

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')
ACTIVATION_DELAY = config.get('gestures.activation_delay')

# --- НАСТРОЙКИ СГЛАЖИВАНИЯ КУРСОРА ---
SMOOTHING_LEVEL = config.get('cursor.smoothing_level')

# --- НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ---
PROCESS_PRIORITY_HIGH = True

# --- НАСТРОЙКИ УПРАВЛЕНИЯ РУКАМИ ---

CONTROL_HAND = config.get('cursor.control_hand')  # 'left', 'right', 'auto'

class AdvancedCursorController:
    def __init__(self):
        self.running = True
        self.frame_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.lock = threading.Lock()

        self.hand_data = {
            'left': {'landmarks': None, 'center': None, 'target_pos': None, 'handedness': None},
            'right': {'landmarks': None, 'center': None, 'target_pos': None, 'handedness': None}
        }

        # Переменные для сглаживания курсора
        self.smoothed_x = None
        self.smoothed_y = None

        # Коэффициент сглаживания
        self.smoothing_speed = max(0.01, 1.0 - SMOOTHING_LEVEL)

        # Устанавливаем высокий приоритет процесса
        if PROCESS_PRIORITY_HIGH:
            try:
                p = psutil.Process(os.getpid())
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                print(f"Приоритет процесса установлен: HIGH")
            except Exception as e:
                print(f"Не удалось установить приоритет процесса: {e}")

        print("Инициализация модели MediaPipe...")
        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            # Изменяем num_hands на 2 для обнаружения обеих рук
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,  # <-- Важно: отслеживаем до 2 рук
                min_hand_detection_confidence=0.55,
                min_tracking_confidence=0.45
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
            print("Модель успешно загружена.")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self.running = False
            return

        self.screen_width, self.screen_height = pyautogui.size()
        print(f"Разрешение экрана: {self.screen_width}x{self.screen_height}")

        self.cap = cv2.VideoCapture(0)
        # Проверить все возможные индексы камер

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.current_frame = None
        self.fps = 0
        self.last_fps_time = time.time()
        self.frame_count = 0

        self.gesture_recognizer = GestureRecognizer()

        # Переменная для хранения ID выбранной руки для управления курсором
        self.active_hand = None  # 'left' или 'right'
        self.active_hand_detected = False
        self.last_active_hand_update = time.time()
        self.setup_config_watcher()

    def setup_config_watcher(self):
        """Настраивает отслеживание изменений настроек"""

        class SettingsHandler(FileSystemEventHandler):
            def __init__(self, controller):
                self.controller = controller

            def on_modified(self, event):
                if event.src_path.endswith('settings.json'):
                    print("Detected settings.json change")
                    self.controller.reload_settings()

        # Определяем путь к файлу настроек
        script_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(script_dir, 'config', 'settings.json')
        config_dir = os.path.dirname(settings_path)

        if os.path.exists(config_dir):
            self.config_observer = Observer()
            event_handler = SettingsHandler(self)
            self.config_observer.schedule(event_handler, path=config_dir, recursive=False)
            self.config_observer.start()
            print(f"Watching for config changes in: {config_dir}")

    def reload_settings(self):
        """Перезагружает настройки и обновляет переменные в реальном времени"""
        global SENSITIVITY_ZONE_PERCENT, SENSITIVITY_ZONE_X, SENSITIVITY_ZONE_Y
        global PADDING, CLICK_DISTANCE_THRESHOLD, SMOOTHING_LEVEL, CONTROL_HAND, ACTIVATION_DELAY

        # Перезагружаем конфиг
        config.reload()

        # Обновляем глобальные переменные
        with self.lock:  # Используйте существующий lock или создайте новый
            SENSITIVITY_ZONE_PERCENT = config.get('cursor.sensitivity_zone_percent', SENSITIVITY_ZONE_PERCENT)
            SENSITIVITY_ZONE_X = config.get('cursor.sensitivity_zone_X', SENSITIVITY_ZONE_X)
            SENSITIVITY_ZONE_Y = config.get('cursor.sensitivity_zone_Y', SENSITIVITY_ZONE_Y)
            PADDING = config.get('cursor.padding', PADDING)

            # Обновляем порог клика
            new_threshold = config.get('gestures.click_distance_threshold', 0.036)
            CLICK_DISTANCE_THRESHOLD = new_threshold / 100 * SENSITIVITY_ZONE_PERCENT

            # Обновляем сглаживание
            SMOOTHING_LEVEL = config.get('cursor.smoothing_level', SMOOTHING_LEVEL)
            self.smoothing_speed = max(0.01, 1.0 - SMOOTHING_LEVEL)

            # Обновляем контрольную руку
            CONTROL_HAND = config.get('cursor.control_hand', CONTROL_HAND)

            # Обновляем задержку активации жестов
            ACTIVATION_DELAY = config.get('gestures.activation_delay', ACTIVATION_DELAY)

            # Обновляем gesture_recognizer
            if hasattr(self, 'gesture_recognizer'):
                self.gesture_recognizer.update_control_hand(CONTROL_HAND)
                self.gesture_recognizer.update_activation_delay(ACTIVATION_DELAY)
                self.gesture_recognizer.update_click_threshold(CLICK_DISTANCE_THRESHOLD)

        print(f"Settings reloaded: sensitivity_zone={SENSITIVITY_ZONE_PERCENT}%, "
              f"smoothing={SMOOTHING_LEVEL}, control_hand={CONTROL_HAND}, "
              f"activation_delay={ACTIVATION_DELAY}s")

    def capture_thread(self):
        """Поток захвата видео"""
        print("Запуск потока захвата...")
        while self.running:
            success, frame = self.cap.read()
            if success:
                frame = cv2.flip(frame, 1)
                with self.frame_lock:
                    self.current_frame = frame
            time.sleep(0.001)

    def tracking_thread(self):
        """Поток отслеживания рук (обеих)"""
        print("Запуск потока отслеживания...")

        while self.running:
            frame_to_process = None
            with self.frame_lock:
                if self.current_frame is not None:
                    frame_to_process = self.current_frame.copy()
                    actual_height, actual_width = frame_to_process.shape[:2]

            if frame_to_process is not None:
                # === БЕРЁМ АКТУАЛЬНЫЕ ЗНАЧЕНИЯ НАСТРОЕК ===
                current_zone_percent = SENSITIVITY_ZONE_PERCENT
                current_zone_x = SENSITIVITY_ZONE_X
                current_zone_y = SENSITIVITY_ZONE_Y
                current_padding = PADDING

                # Вычисляем зону с актуальными значениями
                zone_width_percent = current_zone_percent / 100.0
                zone_height_percent = current_zone_percent / 100.0

                available_width = actual_width - current_padding
                available_height = actual_height - current_padding

                zone_width = available_width * zone_width_percent
                zone_height = available_height * zone_height_percent

                offset_x = current_padding / 2 + ((available_width - zone_width) / 100.0) * current_zone_x
                offset_y = current_padding / 2 + ((available_height - zone_height) / 100.0) * current_zone_y

                x_min = offset_x / actual_width
                x_max = (offset_x + zone_width) / actual_width
                y_min = offset_y / actual_height
                y_max = (offset_y + zone_height) / actual_height

                # Обработка изображения
                image_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                detection_result = self.landmarker.detect(mp_image)

                # Очищаем данные о руках
                new_hand_data = {
                    'left': {'landmarks': None, 'center': None, 'target_pos': None, 'handedness': None},
                    'right': {'landmarks': None, 'center': None, 'target_pos': None, 'handedness': None}
                }

                # Обрабатываем все обнаруженные руки
                if detection_result.hand_landmarks and detection_result.handedness:
                    for hand_landmarks, handedness_info in zip(detection_result.hand_landmarks,
                                                               detection_result.handedness):
                        hand_type = handedness_info[0].category_name.lower()

                        if hand_type == 'left':
                            hand_type = 'right'
                        else:
                            hand_type = 'left'

                        confidence = handedness_info[0].score

                        wrist_x_rel = hand_landmarks[17].x
                        wrist_y_rel = hand_landmarks[17].y

                        screen_x = np.interp(wrist_x_rel, (x_min, x_max), (0, self.screen_width))
                        screen_y = np.interp(wrist_y_rel, (y_min, y_max), (0, self.screen_height))

                        screen_x = np.clip(screen_x, 0, self.screen_width)
                        screen_y = np.clip(screen_y, 0, self.screen_height)

                        target_pos = (screen_x, screen_y)

                        hand_center = (
                            int(wrist_x_rel * actual_width),
                            int(wrist_y_rel * actual_height)
                        )

                        new_hand_data[hand_type] = {
                            'landmarks': hand_landmarks,
                            'center': hand_center,
                            'target_pos': target_pos,
                            'handedness': hand_type,
                            'confidence': confidence
                        }

                # Обновляем данные о руках
                with self.data_lock:
                    self.hand_data = new_hand_data

                # --- Логика выбора активной руки ---
                if CONTROL_HAND == 'left':
                    if self.hand_data['left']['landmarks'] is not None:
                        if not self.active_hand_detected or self.active_hand != 'left':
                            self.active_hand = 'left'
                            self.active_hand_detected = True
                    elif self.active_hand == 'left':
                        self.active_hand_detected = False
                else:
                    if self.hand_data['right']['landmarks'] is not None:
                        if not self.active_hand_detected or self.active_hand != 'right':
                            self.active_hand = 'right'
                            self.active_hand_detected = True
                    elif self.active_hand == 'right':
                        self.active_hand_detected = False

                # --- Управление курсором ---
                if self.active_hand_detected and self.active_hand is not None:
                    hand_info = self.hand_data.get(self.active_hand, {})
                    target_pos = hand_info.get('target_pos')

                    if target_pos is not None:
                        smoothed_pos = self.apply_smoothing(target_pos[0], target_pos[1])
                        win32api.SetCursorPos((int(smoothed_pos[0]), int(smoothed_pos[1])))

            else:
                time.sleep(0.001)

    def apply_smoothing(self, target_x, target_y):
        """Применяет сглаживание к координатам курсора"""
        if self.smoothed_x is None or self.smoothed_y is None:
            self.smoothed_x = target_x
            self.smoothed_y = target_y
        else:
            self.smoothed_x = self.smoothed_x + self.smoothing_speed * (target_x - self.smoothed_x)
            self.smoothed_y = self.smoothed_y + self.smoothing_speed * (target_y - self.smoothed_y)
        return (self.smoothed_x, self.smoothed_y)

    def gesture_thread(self):
        """Поток распознавания жестов - получает точки ОБЕИХ рук"""
        while self.running:
            # Собираем точки обеих рук в словарь
            landmarks_dict = {'left': None, 'right': None}
            target_pos = None

            with self.data_lock:
                # Берем точки левой руки (если есть)
                if self.hand_data['left']['landmarks'] is not None:
                    landmarks_dict['left'] = self.hand_data['left']['landmarks']


                # Берем точки правой руки (если есть)
                if self.hand_data['right']['landmarks'] is not None:
                    landmarks_dict['right'] = self.hand_data['right']['landmarks']


            # Передаем словарь с точками обеих рук в recognizer
            self.gesture_recognizer.recognize_and_execute(landmarks_dict)

            time.sleep(0.01)

    def display_thread(self):
        """Поток отображения - показывает обе руки"""
        print("Запуск основного потока отображения...")
        camera_window_name = "Camera Feed"

        cv2.namedWindow(camera_window_name, cv2.WINDOW_AUTOSIZE)

        while self.running:
            with self.frame_lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None

            with self.data_lock:
                left_center = self.hand_data['left'].get('center')
                right_center = self.hand_data['right'].get('center')
                active_hand = self.active_hand

            self.frame_count += 1
            if time.time() - self.last_fps_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_fps_time = time.time()

            if frame is not None:
                # Рисуем бирюзовый прямоугольник зоны отслеживания
                height, width = frame.shape[:2]

                # Вычисляем доступное пространство с учетом отступов 10 пикселей
                available_width = width - PADDING
                available_height = height - PADDING

                # Вычисляем размеры зоны отслеживания
                zone_width = available_width * (SENSITIVITY_ZONE_PERCENT / 100.0)
                zone_height = available_height * (SENSITIVITY_ZONE_PERCENT / 100.0)

                offset_x = PADDING/2 + ((available_width - zone_width) / 100.0) * SENSITIVITY_ZONE_X
                offset_y = PADDING/2 + ((available_height - zone_height) / 100.0) * SENSITIVITY_ZONE_Y

                # Вычисляем координаты прямоугольника
                rect_x1 = int(offset_x)
                rect_y1 = int(offset_y)
                rect_x2 = int(offset_x + zone_width)
                rect_y2 = int(offset_y + zone_height)

                cv2.rectangle(frame, (rect_x1, rect_y1), (rect_x2, rect_y2), (255, 255, 0), 2)

                # Отображаем активную руку для управления курсором (обводим желтым)
                if active_hand == 'left' and left_center:
                    cv2.circle(frame, left_center, 7, (0, 255, 0), cv2.FILLED)
                elif active_hand == 'right' and right_center:
                    cv2.circle(frame, right_center, 7, (0, 255, 0), cv2.FILLED)

                cv2.putText(frame, f"FPS: {self.fps}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Control hand: {self.active_hand.upper() if self.active_hand else 'NONE'}",
                            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                cv2.imshow(camera_window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
            if frame is None:
                time.sleep(0.01)

    def run(self):
        if not self.running: return
        print("Запуск программы...")

        try:

            capture_t = threading.Thread(target=self.capture_thread, daemon=True)
            tracking_t = threading.Thread(target=self.tracking_thread, daemon=True)
            gesture_t = threading.Thread(target=self.gesture_thread, daemon=True)
            capture_t.start()
            tracking_t.start()
            gesture_t.start()
            self.display_thread()
        except Exception as e:
            print(f"Произошла критическая ошибка: {e}")
        finally:
            self.stop()

    def stop(self):
        print("Остановка программы...")
        self.running = False

        # Останавливаем watcher
        if hasattr(self, 'config_observer'):
            self.config_observer.stop()
            self.config_observer.join()

        # Останавливаем простой перезагрузчик
        if hasattr(self, 'config_reloader'):
            self.config_reloader.stop()

        time.sleep(0.5)
        if hasattr(self, 'landmarker'):
            self.landmarker.close()
        self.cap.release()
        cv2.destroyAllWindows()
        print("Программа завершена.")


if __name__ == "__main__":
    app = AdvancedCursorController()
    app.run()