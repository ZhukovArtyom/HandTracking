import cv2
import mediapipe as mp
import time
import numpy as np
import threading
import pyautogui
import psutil
import os

# --- Импорты для прозрачного окна (Windows) ---
import win32gui
import win32con
import win32api

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
MODEL_PATH = 'hand_landmarker.task'
SENSITIVITY_ZONE_PERCENT = 50
CLICK_DISTANCE_THRESHOLD = 0.04
CLICK_COOLDOWN = 0.5
DOUBLE_CLICK_INTERVAL = 1.0  # Интервал для двойного клика (не используется, оставлен для совместимости)
HOLD_THRESHOLD = 0.15  # Время удержания для активации режима перетаскивания (в секундах)
TRANSPARENT_COLOR = (1, 1, 1)

# --- НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ---
PROCESS_PRIORITY_HIGH = True  # Высокий приоритет процесса


class AdvancedCursorController:
    def __init__(self):
        self.running = True
        self.frame_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.hand_data = {}
        self.smoothed_cursor_pos = None
        self.prev_cursor_x, self.prev_cursor_y = 0, 0
        self.last_left_click_time = 0
        self.last_right_click_time = 0

        # Переменные для удержания (drag & drop)
        self.is_dragging = False
        self.drag_start_time = None
        self.drag_activated = False

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

            if frame_to_process is not None:
                image_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                detection_result = self.landmarker.detect(mp_image)
                hand_landmarks, hand_center, target_pos = None, None, None

                if detection_result.hand_landmarks:
                    hand_landmarks = detection_result.hand_landmarks[0]
                    x_coords = [lm.x for lm in hand_landmarks]
                    y_coords = [lm.y for lm in hand_landmarks]
                    center_x_rel = np.mean(x_coords)
                    center_y_rel = np.mean(y_coords)
                    screen_x = np.interp(center_x_rel, (x_margin, 1.0 - x_margin), (0, self.screen_width))
                    screen_y = np.interp(center_y_rel, (y_margin, 1.0 - y_margin), (0, self.screen_height))
                    target_pos = (screen_x, screen_y)
                    hand_center = (int(center_x_rel * CAMERA_WIDTH), int(center_y_rel * CAMERA_HEIGHT))

                with self.data_lock:
                    self.hand_data = {'landmarks': hand_landmarks, 'center': hand_center, 'target_pos': target_pos}
            else:
                time.sleep(0.01)

    def perform_left_click(self, x, y):
        """Выполняет левый клик без перемещения системного курсора"""
        original_pos = win32api.GetCursorPos()

        # Устанавливаем курсор в позицию клика
        win32api.SetCursorPos((int(x), int(y)))

        # Левый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print(f"Левый клик! В точке: ({x}, {y})")

        # Возвращаем курсор в исходную позицию
        win32api.SetCursorPos(original_pos)

    def perform_right_click(self, x, y):
        """Выполняет правый клик без перемещения системного курсора"""
        original_pos = win32api.GetCursorPos()

        # Устанавливаем курсор в позицию клика
        win32api.SetCursorPos((int(x), int(y)))

        # Правый клик
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        print(f"Правый клик! В точке: ({x}, {y})")

        # Возвращаем курсор в исходную позицию
        win32api.SetCursorPos(original_pos)

    def start_drag(self, x, y):
        """Начинает перетаскивание"""
        original_pos = win32api.GetCursorPos()
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        # НЕ возвращаем курсор обратно - оставляем нажатой кнопку
        print(f"Начало перетаскивания в точке: ({x}, {y})")
        return original_pos  # Возвращаем исходную позицию для возможного восстановления

    def end_drag(self, x, y, original_pos):
        """Завершает перетаскивание"""
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        # Возвращаем курсор в исходную позицию
        win32api.SetCursorPos(original_pos)
        print(f"Завершение перетаскивания в точке: ({x}, {y})")

    def click_thread(self):
        """Поток обработки кликов"""
        print("Запуск потока обработки кликов...")
        print(
            "Режимы: указательный+большой - левый клик, безымянный+большой - правый клик, удержание указательного+большого - drag & drop")

        # Для отслеживания предыдущего состояния щипков
        prev_left_pinch = False
        prev_right_pinch = False

        while self.running:
            landmarks, cursor_pos = None, None
            with self.data_lock:
                if 'landmarks' in self.hand_data:
                    landmarks = self.hand_data['landmarks']
                cursor_pos = self.smoothed_cursor_pos

            if landmarks and cursor_pos:
                # Получаем координаты кончиков пальцев
                thumb_tip = landmarks[4]  # Большой палец
                index_tip = landmarks[8]  # Указательный палец
                ring_tip = landmarks[16]  # Безымянный палец

                # Расстояния для щипков
                left_pinch_distance = np.sqrt((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2)
                right_pinch_distance = np.sqrt((thumb_tip.x - ring_tip.x) ** 2 + (thumb_tip.y - ring_tip.y) ** 2)

                current_time = time.time()

                # --- Левый щипок (указательный + большой) ---
                left_pinch = left_pinch_distance < CLICK_DISTANCE_THRESHOLD

                # Обработка левого щипка для drag & drop и кликов
                if left_pinch:
                    # Если не в режиме перетаскивания и щипок только начался
                    if not self.is_dragging and self.drag_start_time is None:
                        self.drag_start_time = current_time
                        self.drag_activated = False

                    # Проверка на удержание для активации drag & drop
                    elif self.drag_start_time is not None and not self.drag_activated:
                        hold_duration = current_time - self.drag_start_time
                        if hold_duration >= HOLD_THRESHOLD:
                            # Активируем режим перетаскивания
                            self.is_dragging = True
                            self.drag_activated = True
                            self.original_mouse_pos = self.start_drag(cursor_pos[0], cursor_pos[1])
                            print("Режим перетаскивания активирован")

                    # Если в режиме перетаскивания, обновляем позицию
                    if self.is_dragging:
                        win32api.SetCursorPos((int(cursor_pos[0]), int(cursor_pos[1])))

                # --- Правый щипок (безымянный + большой) ---
                right_pinch = right_pinch_distance < CLICK_DISTANCE_THRESHOLD

                # Обработка правого клика (только если не в режиме перетаскивания)
                if right_pinch and not prev_right_pinch and not self.is_dragging:
                    if (current_time - self.last_right_click_time) > CLICK_COOLDOWN:
                        self.perform_right_click(cursor_pos[0], cursor_pos[1])
                        self.last_right_click_time = current_time

                # --- Обработка завершения действий ---

                # Если левый щипок закончился
                if prev_left_pinch and not left_pinch:
                    # Если был активирован режим перетаскивания, завершаем его
                    if self.is_dragging:
                        self.end_drag(cursor_pos[0], cursor_pos[1], self.original_mouse_pos)
                        self.is_dragging = False
                        self.drag_start_time = None
                        self.drag_activated = False

                    # Если было удержание, но недостаточное для drag & drop (короткий клик)
                    elif self.drag_start_time is not None and not self.drag_activated:
                        hold_duration = current_time - self.drag_start_time

                        # Если удержание было коротким - это левый клик
                        if hold_duration < HOLD_THRESHOLD and (
                                current_time - self.last_left_click_time) > CLICK_COOLDOWN:
                            self.perform_left_click(cursor_pos[0], cursor_pos[1])
                            self.last_left_click_time = current_time

                        self.drag_start_time = None
                        self.drag_activated = False

                # Обновляем предыдущие состояния
                prev_left_pinch = left_pinch
                prev_right_pinch = right_pinch

                # Сбрасываем таймер удержания, если нет щипка
                if not left_pinch:
                    self.drag_start_time = None
                    self.drag_activated = False

            time.sleep(0.01)

    def display_thread(self):
        """Поток отображения"""
        print("Запуск основного потока отображения...")
        camera_window_name = "Camera Feed"
        cursor_window_name = "Transparent Cursor Overlay"
        cv2.namedWindow(camera_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(cursor_window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(cursor_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        is_transparent_set = False

        while self.running:
            with self.frame_lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None
            with self.data_lock:
                target_pos = self.hand_data.get('target_pos')
                hand_center = self.hand_data.get('center')

            if target_pos:
                if self.smoothed_cursor_pos is None:
                    self.smoothed_cursor_pos = target_pos
                    self.prev_cursor_x, self.prev_cursor_y = target_pos
                curr_x = self.prev_cursor_x + (target_pos[0] - self.prev_cursor_x) / (SENSITIVITY_ZONE_PERCENT / 20.0)
                curr_y = self.prev_cursor_y + (target_pos[1] - self.prev_cursor_y) / (SENSITIVITY_ZONE_PERCENT / 20.0)
                with self.data_lock:
                    self.smoothed_cursor_pos = (int(curr_x), int(curr_y))
                self.prev_cursor_x, self.prev_cursor_y = curr_x, curr_y
            else:
                with self.data_lock:
                    self.smoothed_cursor_pos = None

            self.frame_count += 1
            if time.time() - self.last_fps_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_fps_time = time.time()

            if frame is not None:
                if hand_center:
                    cv2.circle(frame, hand_center, 7, (0, 255, 0), cv2.FILLED)

                # Отображение текущего режима
                mode_text = "Mode: "
                if self.is_dragging:
                    mode_text += "DRAGGING"
                elif self.drag_start_time is not None:
                    # Показываем прогресс удержания
                    hold_progress = min(1.0, (time.time() - self.drag_start_time) / HOLD_THRESHOLD)
                    mode_text += f"HOLDING {int(hold_progress * 100)}%"
                else:
                    mode_text += "READY"

                cv2.putText(frame, mode_text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {self.fps}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Добавляем подсказки по управлению
                cv2.putText(frame, "Left: Index+Thumb", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, "Right: Ring+Thumb", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow(camera_window_name, frame)

            overlay_image = np.full((self.screen_height, self.screen_width, 3), TRANSPARENT_COLOR, dtype=np.uint8)
            with self.data_lock:
                cursor_pos_to_draw = self.smoothed_cursor_pos

            if cursor_pos_to_draw:
                # Всегда рисуем белый круг одинакового размера
                cv2.circle(overlay_image, cursor_pos_to_draw, 10, (255, 255, 255), cv2.FILLED)
                cv2.circle(overlay_image, cursor_pos_to_draw, 10, (0, 0, 0), 1)

            cv2.imshow(cursor_window_name, overlay_image)

            if not is_transparent_set:
                try:
                    hwnd = win32gui.FindWindow(None, cursor_window_name)
                    current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    new_style = current_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
                    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0,
                                                        win32con.LWA_COLORKEY)
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    is_transparent_set = True
                    print("Прозрачность и 'прокликиваемость' для оверлея успешно установлены.")
                except Exception as e:
                    print(f"Не удалось установить прозрачность: {e}")
                    is_transparent_set = True

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