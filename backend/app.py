import cv2
import mediapipe as mp
import time
import numpy as np
import threading
import pyautogui
import psutil
import os
import winreg

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

CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')

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



    def capture_thread(self):
        """Поток захвата видео"""
        print("Запуск потока захвата...")
        while self.running:
            success, frame = self.cap.read()
            if success:
                with self.frame_lock:
                    self.current_frame = cv2.flip(frame, 1)
            time.sleep(0.001)

    def tracking_thread(self):
        """Поток отслеживания рук (обеих)"""
        print("Запуск потока отслеживания...")

        # Вычисляем размеры зоны отслеживания
        zone_width_percent = SENSITIVITY_ZONE_PERCENT / 100.0
        zone_height_percent = SENSITIVITY_ZONE_PERCENT / 100.0

        while self.running:
            frame_to_process = None
            with self.frame_lock:
                if self.current_frame is not None:
                    frame_to_process = self.current_frame.copy()
                    actual_height, actual_width = frame_to_process.shape[:2]

            if frame_to_process is not None:
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
                        # Определяем тип руки (Left или Right)
                        hand_type = handedness_info[0].category_name.lower()  # 'left' или 'right'

                        # ИНВЕРТИРУЕМ ДЛЯ ЗЕРКАЛЬНОГО ОТОБРАЖЕНИЯ

                        if hand_type == 'left':
                            hand_type = 'right'
                        else:
                            hand_type = 'left'

                        confidence = handedness_info[0].score

                        # Вычисляем границы зоны отслеживания
                        zone_width = actual_width * zone_width_percent
                        zone_height = actual_height * zone_height_percent

                        # Вычисляем отступы (расстояние от края кадра до зоны отслеживания)
                        offset_x = ((actual_width - zone_width) / 100.0) * SENSITIVITY_ZONE_X
                        offset_y = ((actual_height - zone_height) / 100.0) * SENSITIVITY_ZONE_Y

                        # Нормализуем границы в диапазон [0, 1] для интерполяции
                        x_min = offset_x / actual_width
                        x_max = (offset_x + zone_width) / actual_width
                        y_min = offset_y / actual_height
                        y_max = (offset_y + zone_height) / actual_height

                        # Получаем координаты запястья (точка 17)
                        wrist_x_rel = hand_landmarks[17].x
                        wrist_y_rel = hand_landmarks[17].y

                        # Вычисляем координаты на экране с использованием динамических границ
                        screen_x = np.interp(wrist_x_rel, (x_min, x_max), (0, self.screen_width))
                        screen_y = np.interp(wrist_y_rel, (y_min, y_max), (0, self.screen_height))

                        # Ограничиваем значения в допустимых пределах
                        screen_x = np.clip(screen_x, 0, self.screen_width)
                        screen_y = np.clip(screen_y, 0, self.screen_height)

                        target_pos = (screen_x, screen_y)

                        hand_center = (
                            int(wrist_x_rel * actual_width),
                            int(wrist_y_rel * actual_height)
                        )

                        # Сохраняем данные для этой руки
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

                # --- Логика выбора активной руки для управления курсором ---
                current_time = time.time()

                # Определяем, какая рука должна управлять курсором
                if CONTROL_HAND == 'left':
                    # Всегда используем левую руку, если она обнаружена
                    if self.hand_data['left']['landmarks'] is not None:
                        if not self.active_hand_detected or self.active_hand != 'left':
                            self.active_hand = 'left'
                            self.active_hand_detected = True

                    elif self.active_hand == 'left':
                        self.active_hand_detected = False


                else:
                    # Всегда используем правую руку, если она обнаружена
                    if self.hand_data['right']['landmarks'] is not None:
                        if not self.active_hand_detected or self.active_hand != 'right':
                            self.active_hand = 'right'
                            self.active_hand_detected = True

                    elif self.active_hand == 'right':
                        self.active_hand_detected = False

                # --- Управление курсором от активной руки ---
                if self.active_hand_detected and self.active_hand is not None:
                    hand_info = self.hand_data.get(self.active_hand, {})
                    target_pos = hand_info.get('target_pos')

                    if target_pos is not None:
                        # ПЕРЕМЕЩАЕМ КУРСОР от активной руки
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

                # Вычисляем размеры зоны отслеживания
                zone_width = width * (SENSITIVITY_ZONE_PERCENT / 100.0)
                zone_height = height * (SENSITIVITY_ZONE_PERCENT / 100.0)

                # Вычисляем отступы (расстояние от края кадра до зоны отслеживания)
                offset_x = ((width - zone_width) / 100.0) * SENSITIVITY_ZONE_X
                offset_y = ((height - zone_height) / 100.0) * SENSITIVITY_ZONE_Y

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
        time.sleep(0.5)
        if hasattr(self, 'landmarker'):
            self.landmarker.close()
        self.cap.release()
        cv2.destroyAllWindows()
        print("Программа завершена.")


if __name__ == "__main__":
    app = AdvancedCursorController()
    app.run()