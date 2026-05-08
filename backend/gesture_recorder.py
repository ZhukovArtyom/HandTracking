import cv2
import mediapipe as mp
import time
import numpy as np
import os

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config_loader import config

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
CAMERA_WIDTH = config.get('camera.width')
CAMERA_HEIGHT = config.get('camera.height')
MODEL_PATH = config.get('model.path')


CLICK_DISTANCE_THRESHOLD = config.get('gestures.click_distance_threshold')

# Радиус кружка точки


# Цвета для разных рук
COLOR_LEFT = (255, 0, 0)  # Синий для левой руки
COLOR_RIGHT = (0, 255, 0)  # Зелёный для правой руки


class HandTrackingVisualizer:

    RADIUS = int(CAMERA_HEIGHT * CLICK_DISTANCE_THRESHOLD / 2)

    def __init__(self):



        print("\nИнициализация модели MediaPipe...")

        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_tracking_confidence=0.5
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

        # Статистика FPS


    def draw_landmarks(self, frame, hand_landmarks, color):
        """Рисует все точки руки на кадре"""
        height, width = frame.shape[:2]

        for landmark in hand_landmarks:
            # Преобразуем нормализованные координаты в пиксельные
            x = int(landmark.x * width)
            y = int(landmark.y * height)

            # Рисуем кружок
            cv2.circle(frame, (x, y), self.RADIUS, color, cv2.FILLED)
            # Добавляем обводку для лучшей видимости



    def run(self):
        """Главный цикл программы"""
        if not self.running:
            print("✗ Не удалось запустить визуализатор")
            return



        while self.running:
            # Захват кадра
            success, frame = self.cap.read()
            if not success:
                print("Ошибка захвата кадра")
                break

            # Зеркальное отображение
            frame = cv2.flip(frame, 1)

            # Конвертация в RGB для MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            # Обнаружение рук
            detection_result = self.landmarker.detect(mp_image)

            # Отрисовка рук
            if detection_result.hand_landmarks and detection_result.handedness:
                for landmarks, handedness_info in zip(detection_result.hand_landmarks,
                                                      detection_result.handedness):
                    hand_type = handedness_info[0].category_name.lower()
                    confidence = handedness_info[0].score

                    # Выбираем цвет в зависимости от руки
                    color = COLOR_LEFT if hand_type == 'left' else COLOR_RIGHT


                    # Рисуем все точки
                    self.draw_landmarks(frame, landmarks, color)



            cv2.putText(frame, f"Point radius: {self.RADIUS}px", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            # Показ кадра
            cv2.imshow('Hand Tracking Visualizer', frame)

            # Выход по клавише 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nЗавершение работы...")
                break

        self.stop()

    def stop(self):
        """Остановка и освобождение ресурсов"""
        self.running = False
        if hasattr(self, 'landmarker') and self.landmarker:
            self.landmarker.close()
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("Программа завершена")


if __name__ == "__main__":
    try:
        visualizer = HandTrackingVisualizer()
        visualizer.run()
    except KeyboardInterrupt:
        print("\nПрерывание пользователем")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback

        traceback.print_exc()