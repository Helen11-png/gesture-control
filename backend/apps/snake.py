# apps/snake.py
import cv2
import mediapipe as mp
from .base_app import BaseGestureApp


class SnakeApp(BaseGestureApp):
    def __init__(self, hands, mp_hands, mp_drawing):
        super().__init__(hands, mp_hands, mp_drawing)
        self.mp_drawing_styles = mp.solutions.drawing_styles
        print(f"MediaPipe версия: {mp.__version__}")
        print("Приложение для отрисовки змейки")
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

        # Отрисовка landmarks
        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style())

        landmarks = hand_landmarks.landmark

        # Координаты указательного пальца
        index_finger_tip = landmarks[8]
        x_index = int(index_finger_tip.x * width)
        y_index = int(index_finger_tip.y * height)

        # Параметры квадрата
        rect_size = 30

        # Координаты квадрата
        start_point = (x_index - rect_size, y_index - rect_size)
        end_point = (x_index + rect_size, y_index + rect_size)

        # Рисуем квадрат с прозрачной заливкой
        overlay = frame.copy()
        cv2.rectangle(overlay, start_point, end_point, (0, 255, 0), -1)
        alpha = 0.3
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Контур квадрата
        cv2.rectangle(frame, start_point, end_point, (0, 255, 0), 2)

        # Красный круг на кончике пальца
        cv2.circle(frame, (x_index, y_index), 12, (0, 0, 255), -1)
        cv2.circle(frame, (x_index, y_index), 15, (255, 255, 255), 2)

        # Отображаем координаты
        cv2.putText(frame, f'X:{x_index}, Y:{y_index}',
                    (x_index + 20, y_index - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return frame