import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math
import time
import json
from .base_app import BaseGestureApp


class CursorMonitoringApp(BaseGestureApp):
    """Улучшенное приложение для управления курсором с настройками"""

    def __init__(self, hands, mp_hands, mp_drawing):
        super().__init__(hands, mp_hands, mp_drawing)

        # Инициализируем стили рисования
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Получаем размер экрана
        self.screen_width, self.screen_height = pyautogui.size()
        print(f"Размер экрана: {self.screen_width}x{self.screen_height}")

        # Загружаем настройки
        self.settings = self.load_default_settings()
        self.load_settings_from_file()

        # Состояния
        self.prev_x, self.prev_y = 0, 0
        self.is_dragging = False
        self.drag_start_time = 0
        self.drag_start_pos = (0, 0)
        self.calibration_points = []  # Для калибровки
        self.calibration_mode = False

        print("Управление курсором активно!")
        print(f"Настройки: {self.settings}")

    def load_default_settings(self):
        """Настройки по умолчанию"""
        return {
            'click_threshold': 0.045,  # Чувствительность клика
            'double_click_threshold': 0.035,  # Чувствительность двойного клика
            'fist_threshold': 0.12,  # Чувствительность кулака
            'cursor_smoothing': 0.25,  # 0-1, чем больше - плавнее
            'cursor_speed': 1.0,  # Скорость курсора
            'deadzone': 0.15,  # Мёртвая зона по краям
            'drag_delay': 0.3,  # Задержка отпускания перетаскивания
            'enable_double_click': True,
            'enable_drag': True,
            'enable_click': True
        }

    def load_settings_from_file(self):
        """Загружаем настройки из файла"""
        try:
            with open('cursor_settings.json', 'r') as f:
                saved = json.load(f)
                self.settings.update(saved)
                print("Настройки загружены из файла")
        except FileNotFoundError:
            print("Используются настройки по умолчанию")

    def save_settings_to_file(self):
        """Сохраняем настройки в файл"""
        with open('cursor_settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        print("Настройки сохранены")

    def exponential_smoothing(self, current, previous, alpha=None):
        """Экспоненциальное сглаживание"""
        if alpha is None:
            alpha = self.settings['cursor_smoothing']
        return alpha * current + (1 - alpha) * previous

    def _distance(self, p1, p2):
        """Вычисление расстояния между двумя точками"""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    def calibrate_screen(self):
        """Калибровка экрана (показываем 4 угла пальцем)"""
        self.calibration_mode = True
        self.calibration_points = []
        print("Режим калибровки: покажите 4 угла экрана пальцем")

    def process_frame(self, frame, hand_landmarks):
        """Обработка одного кадра с жестами"""
        height, width, _ = frame.shape

        # Получаем координаты ключевых точек
        landmarks = hand_landmarks.landmark

        # Координаты пальцев
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        wrist = landmarks[0]

        # Преобразуем в пиксели
        index_x = int(index_tip.x * width)
        index_y = int(index_tip.y * height)

        # 1. УПРАВЛЕНИЕ КУРСОРОМ (улучшенное)
        # Учитываем мёртвую зону
        deadzone = self.settings['deadzone']
        x_normalized = max(deadzone, min(1 - deadzone, index_tip.x))
        y_normalized = max(deadzone, min(1 - deadzone, index_tip.y))

        # Преобразуем с учётом мёртвой зоны
        effective_range = 1 - 2 * deadzone
        cursor_x = np.interp(x_normalized,
                             [deadzone, 1 - deadzone],
                             [0, self.screen_width])
        cursor_y = np.interp(y_normalized,
                             [deadzone, 1 - deadzone],
                             [0, self.screen_height])

        # Ограничиваем
        cursor_x = max(0, min(self.screen_width - 1, cursor_x))
        cursor_y = max(0, min(self.screen_height - 1, cursor_y))

        # Сглаживание
        smooth_x = self.exponential_smoothing(cursor_x, self.prev_x)
        smooth_y = self.exponential_smoothing(cursor_y, self.prev_y)

        # Двигаем курсор
        pyautogui.moveTo(smooth_x, smooth_y, duration=0.05)

        self.prev_x, self.prev_y = smooth_x, smooth_y

        # 2. ОПРЕДЕЛЯЕМ ЖЕСТЫ
        thumb_index_dist = self._distance(thumb_tip, index_tip)
        pinky_ring_dist = self._distance(pinky_tip, ring_tip)

        fingers_to_wrist = [
            self._distance(index_tip, wrist),
            self._distance(middle_tip, wrist),
            self._distance(ring_tip, wrist),
            self._distance(pinky_tip, wrist)
        ]

        # Жест клика
        if (self.settings['enable_click'] and
                thumb_index_dist < self.settings['click_threshold']):
            pyautogui.click()
            cv2.putText(frame, 'CLICK!', (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        # Жест двойного клика
        elif (self.settings['enable_double_click'] and
              pinky_ring_dist < self.settings['double_click_threshold']):
            pyautogui.doubleClick()
            cv2.putText(frame, 'DOUBLE CLICK!', (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

        # Жест перетаскивания (кулак)
        elif (self.settings['enable_drag'] and
              all(dist < self.settings['fist_threshold']
                  for dist in fingers_to_wrist)):

            if not self.is_dragging:
                pyautogui.mouseDown()
                self.is_dragging = True
                self.drag_start_time = time.time()
                self.drag_start_pos = (cursor_x, cursor_y)
                cv2.putText(frame, 'DRAG START', (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            else:
                # Плавное перетаскивание
                pyautogui.dragTo(cursor_x, cursor_y, duration=0.05)
                cv2.putText(frame, 'DRAGGING...', (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        elif self.is_dragging:
            # Заканчиваем перетаскивание с задержкой
            if time.time() - self.drag_start_time > self.settings['drag_delay']:
                pyautogui.mouseUp()
                self.is_dragging = False
                cv2.putText(frame, 'DRAG END', (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)

        # 3. ВИЗУАЛИЗАЦИЯ
        # Рисуем точку на указательном пальце
        cv2.circle(frame, (index_x, index_y), 15, (0, 0, 255), -1)

        # Отображаем координаты и настройки
        info_text = [
            f"Cursor: {int(smooth_x)},{int(smooth_y)}",
            f"Click: {thumb_index_dist:.3f}/{self.settings['click_threshold']:.3f}",
            f"Drag: {self.is_dragging}",
            f"Smooth: {self.settings['cursor_smoothing']}"
        ]

        for i, text in enumerate(info_text):
            cv2.putText(frame, text, (10, 30 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Рисуем landmarks
        self.mp_drawing.draw_landmarks(
            frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style())

        return frame

    def cleanup(self):
        """Очистка ресурсов"""
        if self.is_dragging:
            pyautogui.mouseUp()
        self.save_settings_to_file()
        super().cleanup()