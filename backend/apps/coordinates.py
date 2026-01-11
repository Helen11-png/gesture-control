import cv2
import mediapipe as mp
from .base_app import BaseGestureApp
import numpy as np


class CoordinatesApp(BaseGestureApp):
    """Приложение для отображения координат пальцев"""

    def __init__(self, hands, mp_hands, mp_drawing):
        super().__init__(hands, mp_hands, mp_drawing)
        self.mp_drawing_styles = mp.solutions.drawing_styles
        print(f"MediaPipe версия: {mp.__version__}")
        print("Приложение для отслеживания координат рук")
        print("Нажмите 'q' для выхода")

    def setup(self):
        """Настройка приложения"""
        if not super().setup():
            return False
        print("Камера успешно открыта")
        return True

    def process_frame(self, frame, hand_landmarks):
        """Обработка одного кадра с отображением координат"""
        height, width, _ = frame.shape

        # Рисуем ключевые точки и соединения
        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style())

        # Получаем координаты всех ключевых точек
        landmarks = hand_landmarks.landmark

        # 1. Выделяем указательный палец (индекс 8)
        index_finger_tip = landmarks[8]
        x_index = int(index_finger_tip.x * width)
        y_index = int(index_finger_tip.y * height)

        # Рисуем красную точку на кончике указательного пальца
        cv2.circle(frame, (x_index, y_index), 12, (0, 0, 255), -1)
        cv2.circle(frame, (x_index, y_index), 15, (255, 255, 255), 2)

        # Отображаем координаты указательного пальца
        cv2.putText(frame, f'Index: X:{x_index}, Y:{y_index}',
                    (x_index + 20, y_index - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # 2. Отображаем номер каждой точки
        for idx, landmark in enumerate(landmarks):
            lx = int(landmark.x * width)
            ly = int(landmark.y * height)

            # Меняем цвет в зависимости от типа точки
            if idx in [4, 8, 12, 16, 20]:  # Кончики пальцев
                color = (0, 255, 0)  # Зеленый
                cv2.circle(frame, (lx, ly), 6, color, -1)
            elif idx in [3, 7, 11, 15, 19]:  # Вторые суставы
                color = (255, 255, 0)  # Голубой
            elif idx in [2, 6, 10, 14, 18]:  # Третьи суставы
                color = (255, 165, 0)  # Оранжевый
            elif idx in [1, 5, 9, 13, 17]:  # Четвертые суставы
                color = (255, 0, 255)  # Розовый
            else:  # Ладонь
                color = (200, 200, 200)  # Серый

            # Подписываем номер точки
            cv2.putText(frame, str(idx), (lx + 5, ly),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # 3. Показываем координаты в таблице (только ключевые точки)
        self._draw_coordinates_table(frame, landmarks, height, width)

        # 4. Добавляем заголовок и инструкции
        self._draw_info(frame)

        return frame

    def _draw_coordinates_table(self, frame, landmarks, height, width):
        """Рисует таблицу с координатами ключевых точек"""
        # Ключевые точки для отображения в таблице
        key_points = {
            0: "Wrist",  # Запястье
            4: "Thumb",  # Большой палец
            8: "Index",  # Указательный палец
            12: "Middle",  # Средний палец
            16: "Ring",  # Безымянный палец
            20: "Pinky"  # Мизинец
        }

        # Рисуем таблицу
        y_offset = 80
        for idx, name in key_points.items():
            landmark = landmarks[idx]
            x_px = int(landmark.x * width)
            y_px = int(landmark.y * height)

            # Строка таблицы
            text = f"{name}: ({x_px:3d}, {y_px:3d})"
            cv2.putText(frame, text, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25

    def _draw_info(self, frame):
        """Рисует информационные тексты на кадре"""
        height, width, _ = frame.shape

        # Заголовок
        cv2.putText(frame, 'Hand Coordinates Tracking', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Инструкция
        cv2.putText(frame, 'Press Q to quit', (10, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Легенда цветов
        cv2.putText(frame, 'Index finger (red)', (width - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.putText(frame, 'Fingertips (green)', (width - 200, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, 'Other joints (colors)', (width - 200, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)