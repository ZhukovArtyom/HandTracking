import cv2
import mediapipe as mp
import time
import numpy as np
import threading
import pyautogui
import psutil
import os

# --- Импорты для управления курсором (Windows) ---
import win32api
import win32con

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
MODEL_PATH = 'hand_landmarker.task'
SENSITIVITY_ZONE_PERCENT = 50
CLICK_DISTANCE_THRESHOLD = 0.05
CLICK_COOLDOWN = 0.5
#DOUBLE_CLICK_INTERVAL = 1.0   #Интервал для двойного клика (не используется, оставлен для совместимости)
HOLD_THRESHOLD = 0.15  # Время удержания для активации режима перетаскивания (в секундах)

DRAG_LOSS_TIMEOUT = 0.1  # 0.1 секунды буфера (можно настроить)

# --- НАСТРОЙКИ СГЛАЖИВАНИЯ КУРСОРА ---
SMOOTHING_LEVEL = 0.7  # Уровень сглаживания (0.0 - без сглаживания, 1.0 - максимальное сглаживание)

# --- НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ---
PROCESS_PRIORITY_HIGH = True  # Высокий приоритет процесса


class AdvancedCursorController:
    def __init__(self):
        self.running = True
        self.frame_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.hand_data = {}
        self.last_left_click_time = 0
        self.last_right_click_time = 0

        # Переменные для удержания (drag & drop)
        self.is_dragging = False
        self.drag_start_time = None
        self.drag_activated = False

        # Переменные для сглаживания курсора
        self.smoothed_x = None
        self.smoothed_y = None

        # Коэффициент сглаживания (преобразуем SMOOTHING_LEVEL в коэффициент скорости)
        # При SMOOTHING_LEVEL = 0 -> smoothing_speed = 1.0 (без сглаживания)
        # При SMOOTHING_LEVEL = 1 -> smoothing_speed = 0.01 (максимальное сглаживание)
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
            options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1,
                                                   min_hand_detection_confidence=0.6, min_tracking_confidence=0.5)
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
        """Поток отслеживания руки"""
        print("Запуск потока отслеживания...")
        zone_factor = SENSITIVITY_ZONE_PERCENT / 100.0
        x_margin = (1.0 - zone_factor) / 2.0
        y_margin = (1.0 - zone_factor) / 2.0

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
                hand_landmarks, hand_center, target_pos = None, None, None

                if detection_result.hand_landmarks:
                    hand_landmarks = detection_result.hand_landmarks[0]
                    # Используем точку 0 (запястье) вместо среднего арифметического
                    wrist_x_rel = hand_landmarks[17].x
                    wrist_y_rel = hand_landmarks[17].y
                    screen_x = np.interp(wrist_x_rel, (x_margin, 1.0 - x_margin), (0, self.screen_width))
                    screen_y = np.interp(wrist_y_rel, (y_margin, 1.0 - y_margin), (0, self.screen_height))
                    target_pos = (screen_x, screen_y)
                    hand_center = (
                        int(wrist_x_rel * actual_width),
                        int(wrist_y_rel * actual_height)
                    )

                with self.data_lock:
                    self.hand_data = {'landmarks': hand_landmarks, 'center': hand_center, 'target_pos': target_pos}
            else:
                time.sleep(0.01)

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

    def move_cursor(self, x, y):
        """Перемещает системный курсор в указанную позицию"""
        win32api.SetCursorPos((int(x), int(y)))

    def apply_smoothing(self, target_x, target_y):
        """Применяет сглаживание к координатам курсора"""
        if self.smoothed_x is None or self.smoothed_y is None:
            # Первое значение - без сглаживания
            self.smoothed_x = target_x
            self.smoothed_y = target_y
        else:
            # Экспоненциальное сглаживание с корректной скоростью
            self.smoothed_x = self.smoothed_x + self.smoothing_speed * (target_x - self.smoothed_x)
            self.smoothed_y = self.smoothed_y + self.smoothing_speed * (target_y - self.smoothed_y)

        return (self.smoothed_x, self.smoothed_y)

    def click_thread(self):
        print("Запуск потока обработки кликов...")
        print(
            "Режимы: указательный+большой - левый клик, безымянный+большой - правый клик, удержание указательного+большого - drag & drop")
        print(f"Уровень сглаживания: {SMOOTHING_LEVEL}")

        prev_left_pinch = False
        prev_right_pinch = False

        # Новые переменные для буфера перетаскивания
        drag_loss_time = None  # Время потери трекинга во время перетаскивания

        while self.running:
            landmarks, target_pos = None, None
            with self.data_lock:
                if 'landmarks' in self.hand_data:
                    landmarks = self.hand_data['landmarks']
                target_pos = self.hand_data.get('target_pos')

            if landmarks and target_pos:
                thumb_tip = landmarks[4]
                index_tip = landmarks[8]
                ring_tip = landmarks[16]

                left_pinch_distance = np.sqrt((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2)
                right_pinch_distance = np.sqrt((thumb_tip.x - ring_tip.x) ** 2 + (thumb_tip.y - ring_tip.y) ** 2)

                current_time = time.time()

                # --- Левый щипок ---
                left_pinch = left_pinch_distance < CLICK_DISTANCE_THRESHOLD

                if left_pinch:
                    # Если мы в режиме перетаскивания, сбрасываем таймер потери
                    if self.is_dragging:
                        drag_loss_time = None

                    # Логика активации перетаскивания
                    if not self.is_dragging and self.drag_start_time is None:
                        self.drag_start_time = current_time
                        self.drag_activated = False
                    elif self.drag_start_time is not None and not self.drag_activated:
                        hold_duration = current_time - self.drag_start_time
                        if hold_duration >= HOLD_THRESHOLD:
                            self.is_dragging = True
                            self.drag_activated = True
                            # Сбрасываем сглаживание при начале перетаскивания для точности
                            self.smoothed_x = None
                            self.smoothed_y = None
                            self.start_drag(target_pos[0], target_pos[1])
                            print("Режим перетаскивания активирован")

                    if self.is_dragging:
                        # При перетаскивании применяем сглаживание для плавности
                        smoothed_pos = self.apply_smoothing(target_pos[0], target_pos[1])
                        self.move_cursor(smoothed_pos[0], smoothed_pos[1])

                # --- Если щипка нет, но мы в режиме перетаскивания ---
                elif self.is_dragging:
                    if drag_loss_time is None:
                        # Запоминаем время потери трекинга
                        drag_loss_time = current_time
                    elif current_time - drag_loss_time > DRAG_LOSS_TIMEOUT:
                        # Если потеря превысила таймаут, завершаем перетаскивание
                        self.end_drag(target_pos[0], target_pos[1])
                        self.is_dragging = False
                        self.drag_start_time = None
                        self.drag_activated = False
                        drag_loss_time = None
                        # Сбрасываем сглаживание после завершения перетаскивания
                        self.smoothed_x = None
                        self.smoothed_y = None
                        print("Перетаскивание завершено по таймауту")

                # --- Правый щипок ---
                right_pinch = right_pinch_distance < CLICK_DISTANCE_THRESHOLD

                if right_pinch and not prev_right_pinch and not self.is_dragging:
                    if (current_time - self.last_right_click_time) > CLICK_COOLDOWN:
                        # Для кликов используем текущую позицию со сглаживанием
                        smoothed_pos = self.apply_smoothing(target_pos[0], target_pos[1])
                        self.perform_right_click(smoothed_pos[0], smoothed_pos[1])
                        self.last_right_click_time = current_time

                # --- Обработка завершения обычного (не буферного) режима ---
                if prev_left_pinch and not left_pinch and not self.is_dragging:
                    if self.drag_start_time is not None and not self.drag_activated:
                        hold_duration = current_time - self.drag_start_time
                        if hold_duration < HOLD_THRESHOLD and (
                                current_time - self.last_left_click_time) > CLICK_COOLDOWN:
                            # Для кликов используем текущую позицию со сглаживанием
                            smoothed_pos = self.apply_smoothing(target_pos[0], target_pos[1])
                            self.perform_left_click(smoothed_pos[0], smoothed_pos[1])
                            self.last_left_click_time = current_time
                        self.drag_start_time = None
                        self.drag_activated = False

                # Обновляем состояния
                prev_left_pinch = left_pinch
                prev_right_pinch = right_pinch

                # Сбрасываем таймер удержания если нет щипка и не в режиме перетаскивания
                if not left_pinch and not self.is_dragging:
                    self.drag_start_time = None
                    self.drag_activated = False

                # Перемещаем курсор при обычном движении (если не в режиме перетаскивания) - С СОЛАЖИВАНИЕМ
                if not self.is_dragging:
                    smoothed_pos = self.apply_smoothing(target_pos[0], target_pos[1])
                    self.move_cursor(smoothed_pos[0], smoothed_pos[1])

            time.sleep(0.01)

    def display_thread(self):
        print("Запуск основного потока отображения...")
        camera_window_name = "Camera Feed"

        cv2.namedWindow(camera_window_name, cv2.WINDOW_AUTOSIZE)

        while self.running:
            with self.frame_lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None
            with self.data_lock:
                hand_center = self.hand_data.get('center')

            self.frame_count += 1
            if time.time() - self.last_fps_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_fps_time = time.time()

            if frame is not None:
                if hand_center:
                    cv2.circle(frame, hand_center, 7, (0, 255, 0), cv2.FILLED)

                mode_text = "Mode: "
                if self.is_dragging:
                    mode_text += "DRAGGING"
                elif self.drag_start_time is not None:
                    hold_progress = min(1.0, (time.time() - self.drag_start_time) / HOLD_THRESHOLD)
                    mode_text += f"HOLDING {int(hold_progress * 100)}%"
                else:
                    mode_text += "READY"

                cv2.putText(frame, mode_text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {self.fps}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Smoothing: {SMOOTHING_LEVEL}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (255, 255, 255), 1)
                cv2.putText(frame, "Left: Index+Thumb", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, "Right: Ring+Thumb", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow(camera_window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
            if frame is None:
                time.sleep(0.01)

    def run(self):
        if not self.running: return
        print("Запуск программы...")
        print("Управление:")
        print("  - Указательный + большой пальцы: левый клик (короткое смыкание) или drag & drop (удержание)")
        print("  - Безымянный + большой пальцы: правый клик")
        print(f"  - Время удержания для drag & drop: {HOLD_THRESHOLD}с")
        print(f"  - Уровень сглаживания: {SMOOTHING_LEVEL} (0.0 - без сглаживания, 1.0 - максимальное)")
        print("  - Нажмите 'q' для выхода")

        try:
            capture_t = threading.Thread(target=self.capture_thread, daemon=True)
            tracking_t = threading.Thread(target=self.tracking_thread, daemon=True)
            click_t = threading.Thread(target=self.click_thread, daemon=True)
            capture_t.start()
            tracking_t.start()
            click_t.start()
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