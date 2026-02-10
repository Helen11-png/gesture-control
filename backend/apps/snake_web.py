import random
import time

class SnakeGameWeb:
    def __init__(self):
        self.grid_size = 20
        self.width = 400
        self.height = 400
        self.tile_count_x = self.width // self.grid_size  # 20
        self.tile_count_y = self.height // self.grid_size  # 20

        self.reset()

    def reset(self):
        """Сброс игры"""
        # Змейка из 3 сегментов в центре
        start_x = self.tile_count_x // 2
        start_y = self.tile_count_y // 2

        self.snake = [
            [start_x, start_y],
            [start_x - 1, start_y],
            [start_x - 2, start_y]
        ]

        self.direction = [1, 0]  # Вправо
        self.next_direction = [1, 0]

        self.score = 0
        self.game_over = False
        self.speed = 7  # кадров в секунду
        self.last_update = time.time()

        # Генерируем первую еду
        self.generate_food()

    def generate_food(self):
        """Генерация еды в случайном месте"""
        while True:
            food = [
                random.randint(0, self.tile_count_x - 1),
                random.randint(0, self.tile_count_y - 1)
            ]

            # Проверяем, чтобы еда не появилась на змейке
            if food not in self.snake:
                self.food = food
                break

    def update_direction(self, direction_str):
        """Обновление направления из строки"""
        direction_map = {
            'up': [0, -1],
            'down': [0, 1],
            'left': [-1, 0],
            'right': [1, 0]
        }

        if direction_str in direction_map:
            new_dir = direction_map[direction_str]

            # Не позволяем развернуться на 180 градусов
            # (новая direction не должна быть противоположной текущей)
            if new_dir[0] != -self.direction[0] or new_dir[1] != -self.direction[1]:
                self.next_direction = new_dir

    def update(self):
        """Обновление состояния игры"""
        if self.game_over:
            return

        # Проверяем таймер для обновления
        current_time = time.time()
        if current_time - self.last_update < (1.0 / self.speed):
            return

        self.last_update = current_time

        # Обновляем направление
        self.direction = self.next_direction.copy()

        # Новая голова
        head = self.snake[0].copy()
        head[0] += self.direction[0]
        head[1] += self.direction[1]

        # Проверка столкновений
        if (head[0] < 0 or head[0] >= self.tile_count_x or
                head[1] < 0 or head[1] >= self.tile_count_y or
                head in self.snake):
            self.game_over = True
            return

        # Добавляем новую голову
        self.snake.insert(0, head)

        # Проверяем съедание еды
        if head == self.food:
            self.score += 10
            self.generate_food()

            # Увеличиваем скорость каждые 50 очков
            if self.score % 50 == 0:
                self.speed += 1
        else:
            # Убираем хвост
            self.snake.pop()

    def get_state(self):
        """Возвращает состояние игры в формате для JSON"""
        # Конвертируем координаты сетки в пиксели
        snake_pixels = [
            [segment[0] * self.grid_size, segment[1] * self.grid_size]
            for segment in self.snake
        ]

        food_pixels = [
            self.food[0] * self.grid_size,
            self.food[1] * self.grid_size
        ]

        # Определяем направление как строку
        direction_str = ''
        if self.direction == [0, -1]:
            direction_str = 'up'
        elif self.direction == [0, 1]:
            direction_str = 'down'
        elif self.direction == [-1, 0]:
            direction_str = 'left'
        elif self.direction == [1, 0]:
            direction_str = 'right'

        return {
            'snake': snake_pixels,
            'food': food_pixels,
            'score': self.score,
            'game_over': self.game_over,
            'direction': direction_str,
            'speed': self.speed,
            'grid_size': self.grid_size,
            'length': len(self.snake)
        }