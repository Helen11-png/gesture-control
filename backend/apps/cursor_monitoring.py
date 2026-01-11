import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math
from .base_app import BaseGestureApp


class CursorMonitoringApp(BaseGestureApp):
    """Приложение для управления курсором мыши жестами"""

    def __init__(self, hands, mp_hands, mp_drawing):
        super().__init__(hands, mp_hands, mp_drawing)

        # Инициализируем стили рисования
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Получаем размер экрана
        self.screen_width, self.screen_height = pyautogui.size()
        print(f"Размер экрана: {self.screen_width}x{self.screen_height}")

        # Настройки
        self.smoothing = 3  # Коэффициент сглаживания движений
        self.prev_x, self.prev_y = 0, 0

        # Состояния для перетаскивания
        self.is_dragging = False

        print("Управление курсором активно!")
        print("Инструкции:")
        print("1. Указательный палец - перемещение курсора")
        print("2. Большой и указательный палец вместе - клик")
        print("3. Мизинец и безымянный палец вместе - двойной клик")
        print("4. Показать кулак - перетаскивание")
        print("5. Нажмите 'q' в окне камеры для выхода")

    def setup(self):
        """Настройка приложения"""
        if not super().setup():
            return False

        # Получаем размер кадра камеры
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Размер кадра камеры: {self.frame_width}x{self.frame_height}")

        return True

    def _distance(self, p1, p2):
        """Вычисление расстояния между двумя точками"""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def process_frame(self, frame, hand_landmarks):
        """Обработка одного кадра с жестами"""
        height, width, _ = frame.shape

        # Получаем координаты ключевых точек
        landmarks = hand_landmarks.landmark

        # Координаты кончиков пальцев
        thumb_tip = landmarks[4]  # Большой палец
        index_tip = landmarks[8]  # Указательный палец
        middle_tip = landmarks[12]  # Средний палец
        ring_tip = landmarks[16]  # Безымянный палец
        pinky_tip = landmarks[20]  # Мизинец
        wrist = landmarks[0]  # Запястье

        # Преобразуем в пиксели для отрисовки
        index_x = int(index_tip.x * width)
        index_y = int(index_tip.y * height)

        # 1. УПРАВЛЕНИЕ КУРСОРОМ
        # Преобразуем координаты указательного пальца в координаты экрана
        # Используем центральную область кадра (игнорируем края)
        cursor_x = np.interp(index_tip.x, [0.1, 0.9], [0, self.screen_width])
        cursor_y = np.interp(index_tip.y, [0.1, 0.9], [0, self.screen_height])

        # Ограничиваем координаты экрана
        cursor_x = max(0, min(self.screen_width - 1, cursor_x))
        cursor_y = max(0, min(self.screen_height - 1, cursor_y))

        # Сглаживание движений
        smooth_x = self.prev_x + (cursor_x - self.prev_x) / self.smoothing
        smooth_y = self.prev_y + (cursor_y - self.prev_y) / self.smoothing

        # Перемещаем курсор
        pyautogui.moveTo(smooth_x, smooth_y, duration=0.1)

        self.prev_x, self.prev_y = smooth_x, smooth_y

        # 2. ОПРЕДЕЛЯЕМ ЖЕСТЫ

        # Расстояния между пальцами
        thumb_index_dist = self._distance(thumb_tip, index_tip)
        pinky_ring_dist = self._distance(pinky_tip, ring_tip)

        # Расстояния от пальцев до запястья (для определения кулака)
        fingers_to_wrist = [
            self._distance(index_tip, wrist),
            self._distance(middle_tip, wrist),
            self._distance(ring_tip, wrist),
            self._distance(pinky_tip, wrist)
        ]

        # Жест клика (большой и указательный пальцы)
        if thumb_index_dist < 0.05:  # Пороговое значение
            pyautogui.click()
            cv2.putText(frame, 'CLICK!', (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        # Жест двойного клика (мизинец и безымянный палец)
        elif pinky_ring_dist < 0.03:
            pyautogui.doubleClick()
            cv2.putText(frame, 'DOUBLE CLICK!', (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

        # Жест перетаскивания (кулак)
        elif all(dist < 0.1 for dist in fingers_to_wrist):
            if not self.is_dragging:
                pyautogui.mouseDown()
                self.is_dragging = True
            cv2.putText(frame, 'DRAGGING...', (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        else:
            if self.is_dragging:
                pyautogui.mouseUp()
                self.is_dragging = False

        # Рисуем визуализацию

        # Рисуем точку на указательном пальце
        cv2.circle(frame, (index_x, index_y), 15, (0, 0, 255), -1)

        # Отображаем координаты курсора
        cv2.putText(frame, f'Cursor: {int(cursor_x)},{int(cursor_y)}',
                    (index_x + 20, index_y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Рисуем все ключевые точки (опционально)
        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style())

        # Отображаем инструкции
        self._draw_instructions(frame)

        return frame

    def _draw_instructions(self, frame):
        """Рисует инструкции на кадре"""
        cv2.putText(frame, 'Gesture Mouse Control', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, 'Index finger: Move cursor', (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, 'Thumb+Index: Click', (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, 'Pinky+Ring: Double click', (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, 'Fist: Drag & drop', (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, 'Press Q to quit', (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    def cleanup(self):
        """Очистка ресурсов"""
        if self.is_dragging:
            pyautogui.mouseUp()
        super().cleanup()