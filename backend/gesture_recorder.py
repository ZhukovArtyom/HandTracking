import cv2
import mediapipe as mp
import time
import numpy as np
import os
import itertools
import base64
import threading
import sys

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config_loader import config

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = config.get('camera.width')
CAMERA_HEIGHT = config.get('camera.height')
MODEL_PATH = config.get('model.path')

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

                        # Отрисовка рук
                        if detection_result.hand_landmarks and detection_result.handedness:
                            for landmarks, handedness_info in zip(detection_result.hand_landmarks,
                                                                  detection_result.handedness):
                                hand_type = handedness_info[0].category_name.lower()
                                landmarks_dict[hand_type] = landmarks

                        # Находим группы пересекающихся точек
                        intersecting_groups = self.find_intersecting_point_groups(landmarks_dict)

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

                        else:
                            print(f"POINT_GROUPS:[\"ЖЕСТ НЕ РАСПОЗНАН\"]")
            except:
                pass
            time.sleep(0.01)

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

        # Преобразуем hand_type в нужный формат (main - правая, second - левая)
        def get_point_label(hand_type, index):
            if hand_type == 'left':
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