# apps/snake.py
import cv2
import mediapipe as mp
import numpy as np
import random
import time
from .base_app import BaseGestureApp


class SnakeGame:
    """Логика игры змейка"""

    def __init__(self, width=800, height=600, grid_size=20):
        self.width = width
        self.height = height
        self.grid_size = grid_size
        self.reset_game()

    def reset_game(self):
        """Сброс игры"""
        # Начальная позиция змейки (3 сегмента)
        start_x = self.width // 2
        start_y = self.height // 2
        self.snake = [
            [start_x, start_y],
            [start_x - self.grid_size, start_y],
            [start_x - 2 * self.grid_size, start_y]
        ]
        self.direction = "RIGHT"
        self.next_direction = "RIGHT"
        self.food = self.generate_food()
        self.score = 0
        self.game_over = False
        self.last_move_time = time.time()
        self.move_delay = 0.15  # секунд между движениями
        self.speed_increase = 0.005  # ускорение за каждую еду

    def generate_food(self):
        """Генерация еды в случайном месте"""
        while True:
            x = random.randint(0, (self.width - self.grid_size) // self.grid_size) * self.grid_size
            y = random.randint(0, (self.height - self.grid_size) // self.grid_size) * self.grid_size
            food_pos = [x, y]

            # Проверяем, чтобы еда не появилась на змейке
            if food_pos not in self.snake:
                return food_pos

    def update_direction(self, gesture_direction):
        """Обновление направления жестом"""
        # Предотвращаем разворот на 180 градусов
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}

        if gesture_direction and gesture_direction != opposites.get(self.direction):
            self.next_direction = gesture_direction

    def update(self):
        """Обновление состояния игры"""
        if self.game_over:
            return False

        current_time = time.time()
        if current_time - self.last_move_time < self.move_delay:
            return True

        # Обновляем направление
        self.direction = self.next_direction

        # Получаем новую голову
        head = self.snake[0].copy()

        if self.direction == "UP":
            head[1] -= self.grid_size
        elif self.direction == "DOWN":
            head[1] += self.grid_size
        elif self.direction == "LEFT":
            head[0] -= self.grid_size
        elif self.direction == "RIGHT":
            head[0] += self.grid_size

        # Проверка столкновений
        if (head[0] < 0 or head[0] >= self.width or
                head[1] < 0 or head[1] >= self.height or
                head in self.snake):
            self.game_over = True
            return False

        # Добавляем новую голову
        self.snake.insert(0, head)

        # Проверяем съедание еды
        if head == self.food:
            self.score += 10
            self.food = self.generate_food()
            # Увеличиваем скорость
            self.move_delay = max(0.05, self.move_delay - self.speed_increase)
        else:
            # Удаляем хвост, если не съели еду
            self.snake.pop()

        self.last_move_time = current_time
        return True

    def get_gesture_direction(self, index_x, index_y, prev_x, prev_y, threshold=30):
        """Определяем направление по движению пальца"""
        dx = index_x - prev_x
        dy = index_y - prev_y

        # Только если движение достаточно большое
        if abs(dx) < threshold and abs(dy) < threshold:
            return None

        # Определяем преобладающее направление
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > 0 else "LEFT"
        else:
            return "DOWN" if dy > 0 else "UP"


class SnakeApp(BaseGestureApp):
    def __init__(self, hands, mp_hands, mp_drawing):
        super().__init__(hands, mp_hands, mp_drawing)
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Инициализация игры
        self.game = SnakeGame(width=800, height=600, grid_size=20)

        # Для отслеживания движения пальца
        self.prev_finger_pos = None
        self.gesture_threshold = 40  # пикселей для регистрации жеста

        # Для рисования
        self.game_canvas = None

        print("🐍 Змейка жестами!")
        print("Управление:")
        print("  👆 Палец вверх - движение вверх")
        print("  👇 Палец вниз - движение вниз")
        print("  👈 Палец влево - движение влево")
        print("  👉 Палец вправо - движение вправо")
        print("  ✊ Кулак - пауза/рестарт")
        print("Нажмите 'q' для выхода")

    def setup(self):
        """Настройка приложения"""
        if not super().setup():
            return False
        print("Камера успешно открыта")

        # Создаём canvas для игры (отдельно от видео)
        self.game_canvas = np.zeros((600, 800, 3), dtype=np.uint8)

        return True

    def detect_fist(self, landmarks):
        """Определение жеста кулака"""
        wrist = landmarks[0]
        fingertips = [4, 8, 12, 16, 20]  # Кончики пальцев

        distances = []
        for tip_idx in fingertips:
            tip = landmarks[tip_idx]
            dist = np.sqrt((tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2)
            distances.append(dist)

        # Если все пальцы близко к запястью - это кулак
        return all(d < 0.15 for d in distances)

    def process_frame(self, frame, hand_landmarks):
        """Обработка кадра и отрисовка игры"""
        height, width, _ = frame.shape

        # Рисуем landmarks руки
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

        # Отображаем точку на пальце
        cv2.circle(frame, (x_index, y_index), 15, (0, 0, 255), -1)
        cv2.circle(frame, (x_index, y_index), 18, (255, 255, 255), 2)

        # Определяем жест
        is_fist = self.detect_fist(landmarks)

        if is_fist:
            # Кулак = рестарт игры
            self.game.reset_game()
            cv2.putText(frame, "RESTART!", (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        else:
            # Определяем направление движения пальца
            if self.prev_finger_pos:
                prev_x, prev_y = self.prev_finger_pos
                direction = self.game.get_gesture_direction(
                    x_index, y_index, prev_x, prev_y, self.gesture_threshold
                )

                if direction:
                    self.game.update_direction(direction)
                    # Показываем направление на экране
                    cv2.putText(frame, f"Direction: {direction}",
                                (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (255, 255, 0), 2)

            self.prev_finger_pos = (x_index, y_index)

        # Обновляем игру
        if not self.game.game_over:
            self.game.update()

        # Создаём canvas для игры
        self.game_canvas = np.zeros((600, 800, 3), dtype=np.uint8)

        # Рисуем сетку (опционально)
        grid_color = (40, 40, 40)
        for x in range(0, 800, self.game.grid_size):
            cv2.line(self.game_canvas, (x, 0), (x, 600), grid_color, 1)
        for y in range(0, 600, self.game.grid_size):
            cv2.line(self.game_canvas, (0, y), (800, y), grid_color, 1)

        # Рисуем змейку
        for i, segment in enumerate(self.game.snake):
            color = (0, 255, 0) if i == 0 else (0, 200, 0)  # Голова ярче
            x, y = segment
            cv2.rectangle(self.game_canvas,
                          (x, y),
                          (x + self.game.grid_size - 2, y + self.game.grid_size - 2),
                          color, -1)

            # Глаза у головы
            if i == 0:
                eye_size = self.game.grid_size // 4
                eye_offset = self.game.grid_size // 3

                # Левый глаз
                if self.game.direction == "RIGHT":
                    cv2.circle(self.game_canvas,
                               (x + self.game.grid_size - eye_offset, y + eye_offset),
                               eye_size, (0, 0, 0), -1)
                elif self.game.direction == "LEFT":
                    cv2.circle(self.game_canvas,
                               (x + eye_offset, y + eye_offset),
                               eye_size, (0, 0, 0), -1)
                elif self.game.direction == "UP":
                    cv2.circle(self.game_canvas,
                               (x + eye_offset, y + eye_offset),
                               eye_size, (0, 0, 0), -1)
                    cv2.circle(self.game_canvas,
                               (x + self.game.grid_size - eye_offset, y + eye_offset),
                               eye_size, (0, 0, 0), -1)
                elif self.game.direction == "DOWN":
                    cv2.circle(self.game_canvas,
                               (x + eye_offset, y + self.game.grid_size - eye_offset),
                               eye_size, (0, 0, 0), -1)
                    cv2.circle(self.game_canvas,
                               (x + self.game.grid_size - eye_offset,
                                y + self.game.grid_size - eye_offset),
                               eye_size, (0, 0, 0), -1)

        # Рисуем еду
        food_x, food_y = self.game.food
        cv2.rectangle(self.game_canvas,
                      (food_x, food_y),
                      (food_x + self.game.grid_size - 2,
                       food_y + self.game.grid_size - 2),
                      (0, 0, 255), -1)

        # Добавляем яблочко (стикер)
        cv2.circle(self.game_canvas,
                   (food_x + self.game.grid_size // 2,
                    food_y + self.game.grid_size // 2),
                   self.game.grid_size // 3, (0, 100, 0), -1)

        # Отображаем счёт
        score_text = f"Score: {self.game.score}"
        cv2.putText(self.game_canvas, score_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Отображаем скорость
        speed_text = f"Speed: {1 / self.game.move_delay:.1f}"
        cv2.putText(self.game_canvas, speed_text, (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 200), 2)

        # Если игра окончена
        if self.game.game_over:
            game_over_text = "GAME OVER!"
            cv2.putText(self.game_canvas, game_over_text,
                        (800 // 2 - 150, 600 // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)

            restart_text = "Show FIST to restart"
            cv2.putText(self.game_canvas, restart_text,
                        (800 // 2 - 180, 600 // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # Комбинируем кадр камеры и игру
        combined = self.combine_frames(frame, self.game_canvas)

        return combined

    def combine_frames(self, camera_frame, game_frame):
        """Объединяем кадр камеры и игровое поле"""
        # Уменьшаем кадр камеры
        camera_small = cv2.resize(camera_frame, (300, 225))

        # Создаём объединённый кадр
        combined = np.zeros((600, 800 + 320, 3), dtype=np.uint8)

        # Игровое поле слева
        combined[0:600, 0:800] = game_frame

        # Камера справа сверху
        combined[20:20 + 225, 820:820 + 300] = camera_small

        # Рамка вокруг камеры
        cv2.rectangle(combined, (818, 18), (820 + 302, 20 + 227), (255, 255, 255), 2)

        # Инструкции справа
        instructions = [
            "CONTROLS:",
            "Move finger:",
            "  UP    - Snake up",
            "  DOWN  - Snake down",
            "  LEFT  - Snake left",
            "  RIGHT - Snake right",
            "",
            "FIST: Restart game",
            "",
            f"Score: {self.game.score}",
            f"Speed: {1 / self.game.move_delay:.1f}"
        ]

        y_offset = 280
        for i, line in enumerate(instructions):
            color = (255, 255, 0) if i == 0 else (255, 255, 255)
            cv2.putText(combined, line, (820, y_offset + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        return combined

    def cleanup(self):
        """Очистка ресурсов"""
        print(f"Игра завершена. Финальный счёт: {self.game.score}")
        super().cleanup()