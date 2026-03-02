import cv2
import mediapipe as mp
import time
import numpy as np
import threading
import pyautogui

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
SENSITIVITY_ZONE_PERCENT = 80
CLICK_DISTANCE_THRESHOLD = 0.04
CLICK_COOLDOWN = 0.5
TRANSPARENT_COLOR = (1, 1, 1)


class AdvancedCursorController:
    def __init__(self):
        self.running = True
        self.frame_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.hand_data = {}
        self.smoothed_cursor_pos = None
        self.prev_cursor_x, self.prev_cursor_y = 0, 0
        self.last_click_time = 0

        print("Инициализация модели MediaPipe...")
        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1,
                                                   min_hand_detection_confidence=0.6, min_tracking_confidence=0.5)
            self.landmarker = vision.HandLandmarker.create_from_options(options)
            print("Модель успешно загружена.")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}");
            self.running = False;
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
        print("Запуск потока захвата...")
        while self.running:
            success, frame = self.cap.read()
            if success:
                with self.frame_lock: self.current_frame = cv2.flip(frame, 1)
            time.sleep(0.001)

    def tracking_thread(self):
        print("Запуск потока отслеживания...")
        zone_factor = SENSITIVITY_ZONE_PERCENT / 100.0
        x_margin = (1.0 - zone_factor) / 2.0
        y_margin = (1.0 - zone_factor) / 2.0

        while self.running:
            frame_to_process = None
            with self.frame_lock:
                if self.current_frame is not None: frame_to_process = self.current_frame.copy()

            if frame_to_process is not None:
                image_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                detection_result = self.landmarker.detect(mp_image)
                hand_landmarks, hand_center, target_pos = None, None, None

                if detection_result.hand_landmarks:
                    hand_landmarks = detection_result.hand_landmarks[0]
                    x_coords = [lm.x for lm in hand_landmarks];
                    y_coords = [lm.y for lm in hand_landmarks]
                    center_x_rel = np.mean(x_coords);
                    center_y_rel = np.mean(y_coords)
                    screen_x = np.interp(center_x_rel, (x_margin, 1.0 - x_margin), (0, self.screen_width))
                    screen_y = np.interp(center_y_rel, (y_margin, 1.0 - y_margin), (0, self.screen_height))
                    target_pos = (screen_x, screen_y)
                    hand_center = (int(center_x_rel * CAMERA_WIDTH), int(center_y_rel * CAMERA_HEIGHT))

                with self.data_lock:
                    self.hand_data = {'landmarks': hand_landmarks, 'center': hand_center, 'target_pos': target_pos}
            else:
                time.sleep(0.01)

    def click_thread(self):
        print("Запуск потока обработки кликов...")
        while self.running:
            landmarks, cursor_pos = None, None
            with self.data_lock:
                if 'landmarks' in self.hand_data:
                    landmarks = self.hand_data['landmarks']
                cursor_pos = self.smoothed_cursor_pos

            if landmarks and cursor_pos:
                thumb_tip = landmarks[4]
                index_tip = landmarks[8]
                distance = np.sqrt((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2)

                if distance < CLICK_DISTANCE_THRESHOLD and (time.time() - self.last_click_time) > CLICK_COOLDOWN:
                    # Сохраняем текущую позицию мыши
                    original_pos = win32api.GetCursorPos()

                    # Эмулируем клик в позиции курсора-кружка без перемещения системного курсора
                    win32api.SetCursorPos((int(cursor_pos[0]), int(cursor_pos[1])))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

                    # Возвращаем курсор в исходную позицию
                    win32api.SetCursorPos(original_pos)

                    print(f"Клик! В точке: {cursor_pos}")
                    self.last_click_time = time.time()
            time.sleep(0.01)

    def display_thread(self):
        print("Запуск основного потока отображения...")
        camera_window_name = "Camera Feed";
        cursor_window_name = "Transparent Cursor Overlay"
        cv2.namedWindow(camera_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(cursor_window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(cursor_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        is_transparent_set = False

        while self.running:
            with self.frame_lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None
            with self.data_lock:
                target_pos = self.hand_data.get('target_pos');
                hand_center = self.hand_data.get('center')

            if target_pos:
                if self.smoothed_cursor_pos is None:
                    self.smoothed_cursor_pos = target_pos;
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
            if time.time() - self.last_fps_time >= 1.0: self.fps = self.frame_count; self.frame_count = 0; self.last_fps_time = time.time()
            if frame is not None:
                if hand_center: cv2.circle(frame, hand_center, 7, (0, 255, 0), cv2.FILLED)
                cv2.putText(frame, f"FPS: {self.fps}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow(camera_window_name, frame)

            overlay_image = np.full((self.screen_height, self.screen_width, 3), TRANSPARENT_COLOR, dtype=np.uint8)
            with self.data_lock:
                cursor_pos_to_draw = self.smoothed_cursor_pos
            if cursor_pos_to_draw:
                cv2.circle(overlay_image, cursor_pos_to_draw, 10, (255, 255, 255), cv2.FILLED)
                cv2.circle(overlay_image, cursor_pos_to_draw, 10, (0, 0, 0), 1)
            cv2.imshow(cursor_window_name, overlay_image)

            if not is_transparent_set:
                try:
                    hwnd = win32gui.FindWindow(None, cursor_window_name)

                    ### ГЛАВНОЕ ИЗМЕНЕНИЕ: Добавляем стиль WS_EX_TRANSPARENT ###
                    # Этот стиль делает окно "прозрачным" для кликов мыши
                    current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    new_style = current_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
                    ###########################################################

                    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0,
                                                        win32con.LWA_COLORKEY)
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    is_transparent_set = True
                    print("Прозрачность и 'прокликиваемость' для оверлея успешно установлены.")
                except Exception as e:
                    print(f"Не удалось установить прозрачность: {e}");
                    is_transparent_set = True

            if cv2.waitKey(1) & 0xFF == ord('q'): self.running = False; break
            if frame is None: time.sleep(0.01)

    def run(self):
        if not self.running: return
        print("Запуск программы...")
        try:
            capture_t = threading.Thread(target=self.capture_thread, daemon=True)
            tracking_t = threading.Thread(target=self.tracking_thread, daemon=True)
            click_t = threading.Thread(target=self.click_thread, daemon=True)
            capture_t.start();
            tracking_t.start();
            click_t.start()
            self.display_thread()
        except Exception as e:
            print(f"Произошла критическая ошибка: {e}")
        finally:
            self.stop()

    def stop(self):
        print("Остановка программы...");
        self.running = False;
        time.sleep(0.5)
        if hasattr(self, 'landmarker'): self.landmarker.close()
        self.cap.release();
        cv2.destroyAllWindows();
        print("Программа завершена.")


if __name__ == "__main__":
    app = AdvancedCursorController()
    app.run()