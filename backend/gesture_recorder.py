import cv2
import mediapipe as mp
import time
import numpy as np

import base64
import threading
import sys
import os

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Для режима разработки
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Для собранного приложения добавляем resources/backend
if getattr(sys, 'frozen', False):
    resources_dir = os.path.join(os.path.dirname(sys.executable), 'resources', 'backend')
    if resources_dir not in sys.path:
        sys.path.insert(0, resources_dir)

from config_loader import config

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = config.get('camera.width')
CAMERA_HEIGHT = config.get('camera.height')
MODEL_PATH = config.get('model.path')

CONTROL_HAND = config.get('cursor.control_hand')


CLICK_DISTANCE_THRESHOLD = 0.06


class GestureRecorder:

    def __init__(self):
        print("\nИнициализация модели MediaPipe...")

        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.55,
                min_tracking_confidence=0.45
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
            print("✓ Модель успешно загружена")
        except Exception as e:
            print(f"✗ Ошибка загрузки модели: {e}")
            self.landmarker = None
            return

        # Инициализация камеры
        print("Инициализация камеры...")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        # Проверка камеры
        if not self.cap.isOpened():
            print("✗ Ошибка: Не удалось открыть камеру")
            self.running = False
            return

        print("✓ Камера успешно запущена")

        self.running = True

        self.frame_lock = threading.Lock()
        self.current_frame = None

    def capture_thread(self):
        """Поток захвата видео"""
        print("Запуск потока захвата...")
        while self.running:
            success, frame = self.cap.read()
            if success:
                frame = cv2.flip(frame, 1)
                with self.frame_lock:
                    self.current_frame = frame

                # Кодируем кадр в JPEG, затем в base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')

                # Отправляем в Electron через stdout (с префиксом FRAME:)
                print(f"FRAME:{frame_base64}")
            time.sleep(0.001)



    def gesture_recording_thread(self):
        """Поток для прослушивания команд из stdin"""
        print("Запуск потока прослушивания команд...")
        while self.running:
            try:
                command = sys.stdin.readline().strip()
                if command == 'RECORD_GESTURE':


                    frame_to_process = None
                    with self.frame_lock:
                        if self.current_frame is not None:
                            frame_to_process = self.current_frame.copy()

                    if frame_to_process is not None:
                        # Конвертация в RGB для MediaPipe
                        frame_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

                        # Обнаружение рук
                        detection_result = self.landmarker.detect(mp_image)

                        # Подготовка данных для анализа пересечений
                        landmarks_dict = {'right': None, 'left': None}
                        hands_detected = {'right': False, 'left': False}

                        # Отрисовка рук
                        if detection_result.hand_landmarks and detection_result.handedness:
                            for landmarks, handedness_info in zip(detection_result.hand_landmarks,
                                                                  detection_result.handedness):
                                hand_type = handedness_info[0].category_name.lower()

                                if hand_type == 'left':
                                    hand_type = 'right'
                                else:
                                    hand_type = 'left'

                                landmarks_dict[hand_type] = landmarks
                                hands_detected[hand_type] = True

                        # Находим группы пересекающихся точек
                        intersecting_groups = self.find_intersecting_point_groups(landmarks_dict)

                        if hands_detected['right'] and hands_detected['left'] and intersecting_groups:
                            # Проверяем, есть ли в группах точки из обеих рук
                            has_main = False
                            has_second = False
                            for group in intersecting_groups:
                                if any('main' in point for point in group):
                                    has_main = True
                                if any('second' in point for point in group):
                                    has_second = True
                                if has_main and has_second:
                                    break

                            # Если нет групп с точками из обеих рук - жест некорректный
                            if not (has_main and has_second):
                                print(f"POINT_GROUPS:[\"НЕКОРРЕКТНЫЙ ДВУРУЧНЫЙ ЖЕСТ\"]")
                                continue

                        if intersecting_groups:
                            # Форматируем вывод
                            can_send = True
                            output_str = str(intersecting_groups)

                            if 'main' in output_str and 'second' in output_str:
                                cross_hand = False
                                for group in intersecting_groups:
                                    # Проверяем, содержит ли группа точки с разными руками
                                    has_main = any('main' in point for point in group)
                                    has_second = any('second' in point for point in group)

                                    if has_main and has_second:
                                        cross_hand = True
                                        break
                                if not cross_hand:
                                    print(f"POINT_GROUPS:[\"НЕКОРРЕКТНЫЙ ДВУРУЧНЫЙ ЖЕСТ\"]")
                                    can_send = False

                            if can_send:
                                output_str = output_str.replace("'", '"')
                                print(f"POINT_GROUPS:{output_str}")

                                icon = self.generate_gesture_image(frame_to_process, landmarks_dict)
                                if icon is not None:
                                    _, buffer = cv2.imencode('.png', icon, [cv2.IMWRITE_PNG_COMPRESSION, 5])
                                    icon_base64 = base64.b64encode(buffer).decode('utf-8')
                                    print(f"ICON:{icon_base64}")
                        else:
                            print(f"POINT_GROUPS:[\"ЖЕСТ НЕ РАСПОЗНАН\"]")
            except:
                pass
            time.sleep(0.01)

    def generate_gesture_image(self, frame, landmarks_dict):

        try:
            # Создаем изображение с синим фоном
            height, width = frame.shape[:2]
            base = np.full((height, width, 4), (0, 0, 0, 0), dtype=np.uint8)  # прозрачное базовое пространство

            # Собираем все точки для bounding box
            all_points = []

            # Рисуем скелеты рук на синем фоне
            for hand_type, landmarks in landmarks_dict.items():
                if landmarks is None:
                    continue

                # Вычисляем толщину для линий относительно длины ладони
                point0_x = landmarks[0].x * width
                point0_y = landmarks[0].y * height
                point5_x = landmarks[5].x * width
                point5_y = landmarks[5].y * height
                line_thinkness = int(np.sqrt((point0_x - point5_x) ** 2 + (point0_y - point5_y) ** 2) / 5)

                # Вычисление точки костяшки запястья
                current_0 = landmarks[0]
                current_17 = landmarks[17]
                ux = 0.3
                uy = 0.2

                new_x = int((current_0.x + ux * (current_17.x - current_0.x)) * width)
                new_y = int((current_0.y + uy * (current_17.y - current_0.y)) * height)

                # точки для отрисовки ладони
                palm_points = np.array([[new_x, new_y],
                                        [int(landmarks[1].x * width), int(landmarks[1].y * height)],
                                        [int(landmarks[2].x * width), int(landmarks[2].y * height)],
                                        [int(landmarks[5].x * width), int(landmarks[5].y * height)],
                                        [int(landmarks[9].x * width), int(landmarks[9].y * height)],
                                        [int(landmarks[13].x * width), int(landmarks[13].y * height)],
                                        [int(landmarks[17].x * width), int(landmarks[17].y * height)]
                                        ], dtype=np.int32)

                # Рисуем ладонь (СНАЧАЛА)
                cv2.polylines(base, [palm_points], True, (230, 230, 230, 255), 5)
                cv2.fillPoly(base, [palm_points], (255, 255, 255, 255))


                # Добавляем точки ладони в all_points
                for point in palm_points:
                    all_points.append((point[0], point[1]))


                # Соединяем точки пальцев линиями
                connections = [
                    (2, 3), (3, 4),  # Большой палец
                    (5, 6), (6, 7), (7, 8),  # Указательный палец
                    (9, 10), (10, 11), (11, 12),  # Средний палец
                    (13, 14), (14, 15), (15, 16),  # Безымянный палец
                    (17, 18), (18, 19), (19, 20),  # Мизинец
                ]

                # Рисуем линии пальцев
                for connection in connections:
                    idx1, idx2 = connection
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        x1 = int(landmarks[idx1].x * width)
                        y1 = int(landmarks[idx1].y * height)
                        x2 = int(landmarks[idx2].x * width)
                        y2 = int(landmarks[idx2].y * height)
                        cv2.line(base, (x1, y1), (x2, y2), (230, 230, 230, 255), line_thinkness)
                        cv2.line(base, (x1, y1), (x2, y2), (255, 255, 255, 255), line_thinkness - 5)  # Белые линии
                        all_points.append((x1, y1))
                        all_points.append((x2, y2))

            # Обрезаем до содержимого (находим bounding box всех точек)
            if all_points:
                # Находим границы
                points_array = np.array(all_points)
                min_x = max(0, np.min(points_array[:, 0]) - 10)
                max_x = min(width, np.max(points_array[:, 0]) + 10)
                min_y = max(0, np.min(points_array[:, 1]) - 10)
                max_y = min(height, np.max(points_array[:, 1]) + 10)

                # Обрезаем изображение
                cropped = base[min_y:max_y, min_x:max_x]

                # Добавляем поля (отступ)
                h, w = cropped.shape[:2]
                bordered = np.full((h + 40, w + 40, 4), (0, 0, 0, 0), dtype=np.uint8)
                bordered[20:20 + h, 20:20 + w] = cropped

                # если основная рука левая, отзеркаливаем изображение для правильного отображения в интерфейсе
                if CONTROL_HAND == 'left':
                    bordered = cv2.flip(bordered, 1)

                return bordered

            return None

        except Exception as e:
            print(f"Ошибка генерации изображения жеста: {e}")
            return None




    def calculate_distance(self, point1, point2):
        """Вычисляет расстояние между двумя точками в нормализованных координатах"""
        return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

    def find_intersecting_point_groups(self, landmarks_dict):
        """
        Находит группы точек, которые пересекаются (находятся ближе порога)
        Использует только ключевые точки: 4,8,12,16,20,1,5,9,13,17
        Возвращает список попарных групп точек в формате [["main_4", "main_8"], ["main_8", "main_12"], ...]
        """
        # Ключевые точки, которые участвуют в распознавании
        KEY_POINTS = {4, 8, 12, 16, 20, 1}

        # Собираем только ключевые точки из всех рук
        all_points = []  # (hand_type, index, point_obj)

        for hand_type, landmarks in landmarks_dict.items():
            if landmarks is not None:
                for i, point in enumerate(landmarks):
                    if i in KEY_POINTS:  # Фильтруем только ключевые точки
                        all_points.append((hand_type, i, point))

        if len(all_points) < 2:
            return []

        # Находим все пары точек, расстояние между которыми меньше порога
        pairs = []
        for i, (hand1, idx1, point1) in enumerate(all_points):
            for j, (hand2, idx2, point2) in enumerate(all_points):
                if i >= j:
                    continue
                distance = self.calculate_distance(point1, point2)
                if distance <= CLICK_DISTANCE_THRESHOLD:
                    pairs.append((i, j))

        if not pairs:
            return []

        # Преобразуем hand_type в нужный формат
        def get_point_label(hand_type, index):
            if hand_type == CONTROL_HAND:
                return f"main_{index}"
            else:
                return f"second_{index}"

        # Создаём попарные группы
        groups = []
        for pair in pairs:
            i, j = pair
            hand1, idx1, _ = all_points[i]
            hand2, idx2, _ = all_points[j]
            point1_label = get_point_label(hand1, idx1)
            point2_label = get_point_label(hand2, idx2)
            groups.append([point1_label, point2_label])

        # Удаляем дубликаты (порядок точек не важен)
        unique_groups = []
        for group in groups:
            # Сортируем для нормализации
            sorted_group = sorted(group)
            if sorted_group not in unique_groups:
                unique_groups.append(sorted_group)

        return unique_groups

    def run(self):
        """Главный цикл программы"""
        if not self.running:
            print("✗ Не удалось запустить визуализатор")
            return

        # Запускаем потоки
        capture_t = threading.Thread(target=self.capture_thread, daemon=True)
        recording_t = threading.Thread(target=self.gesture_recording_thread, daemon=True)

        capture_t.start()
        recording_t.start()

        # Ждём завершения (бесконечно, пока running=True)
        while self.running:
            time.sleep(0.1)

        self.stop()

    def stop(self):
        """Остановка и освобождение ресурсов"""
        self.running = False
        if hasattr(self, 'landmarker') and self.landmarker:
            self.landmarker.close()
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()

        print("Программа завершена")


if __name__ == "__main__":
    try:
        gesture_recorder = GestureRecorder()
        gesture_recorder.run()
    except KeyboardInterrupt:
        print("\nПрерывание пользователем")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback

        traceback.print_exc()