import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import cv2
import mediapipe as mp
import numpy as np
import json
import asyncio
import base64
import sys
import random
import time  # ДОБАВЬ ЭТО

# Добавляем корневую папку в путь импорта
current_dir = Path(__file__).parent
project_root = current_dir.parent  # gesture/
sys.path.append(str(project_root))

# Создаем FastAPI приложение
app = FastAPI(title="Gesture Control System")

# ПРАВИЛЬНЫЙ путь к frontend
frontend_path = project_root / "frontend"
print(f"Frontend path: {frontend_path}")

# Монтируем статические файлы
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
else:
    print(f"WARNING: Frontend directory not found at {frontend_path}")

# Инициализация MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


# ========== КЛАСС ЗМЕЙКИ ==========
class SnakeGameWeb:
    def __init__(self):
        self.grid_size = 20
        self.width = 400
        self.height = 400
        self.tile_count_x = self.width // self.grid_size
        self.tile_count_y = self.height // self.grid_size
        self.reset()

    def reset(self):
        start_x = self.tile_count_x // 2
        start_y = self.tile_count_y // 2

        self.snake = [
            [start_x, start_y],
            [start_x - 1, start_y],
            [start_x - 2, start_y]
        ]

        self.direction = [1, 0]  # вправо
        self.next_direction = [1, 0]
        self.score = 0
        self.game_over = False
        self.speed = 7
        self.last_update = time.time()
        self.generate_food()

    def generate_food(self):
        while True:
            food = [
                random.randint(0, self.tile_count_x - 1),
                random.randint(0, self.tile_count_y - 1)
            ]
            if food not in self.snake:
                self.food = food
                break

    def update_direction(self, direction_str):
        direction_map = {
            'up': [0, -1],
            'down': [0, 1],
            'left': [-1, 0],
            'right': [1, 0]
        }

        if direction_str in direction_map:
            new_dir = direction_map[direction_str]
            if new_dir[0] != -self.direction[0] or new_dir[1] != -self.direction[1]:
                self.next_direction = new_dir

    def update(self):
        if self.game_over:
            return

        current_time = time.time()
        if current_time - self.last_update < (1.0 / self.speed):
            return

        self.last_update = current_time
        self.direction = self.next_direction.copy()

        head = self.snake[0].copy()
        head[0] += self.direction[0]
        head[1] += self.direction[1]

        if (head[0] < 0 or head[0] >= self.tile_count_x or
                head[1] < 0 or head[1] >= self.tile_count_y or
                head in self.snake):
            self.game_over = True
            return

        self.snake.insert(0, head)

        if head == self.food:
            self.score += 10
            self.generate_food()
            if self.score % 50 == 0:
                self.speed += 1
        else:
            self.snake.pop()

    def get_state(self):
        snake_pixels = [
            [segment[0] * self.grid_size, segment[1] * self.grid_size]
            for segment in self.snake
        ]

        food_pixels = [
            self.food[0] * self.grid_size,
            self.food[1] * self.grid_size
        ]

        return {
            'snake': snake_pixels,
            'food': food_pixels,
            'score': self.score,
            'game_over': self.game_over,
            'speed': self.speed,
            'grid_size': self.grid_size,
            'length': len(self.snake)
        }


# Словарь для хранения игр змейки
snake_games = {}


def get_direction_from_hand(hand_landmarks):
    """Определяем направление по положению ладони"""
    landmarks = hand_landmarks.landmark

    if len(landmarks) < 21:
        return None

    # Центр ладони (упрощенно)
    palm_x = (landmarks[0].x + landmarks[5].x + landmarks[9].x +
              landmarks[13].x + landmarks[17].x) / 5
    palm_y = (landmarks[0].y + landmarks[5].y + landmarks[9].y +
              landmarks[13].y + landmarks[17].y) / 5

    # Относительно запястья
    wrist_x = landmarks[0].x
    wrist_y = landmarks[0].y

    dx = palm_x - wrist_x
    dy = palm_y - wrist_y

    threshold = 0.05

    if abs(dx) < threshold and abs(dy) < threshold:
        return None

    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    else:
        return 'down' if dy > 0 else 'up'


def detect_fist(hand_landmarks):
    """Определяем жест кулака"""
    landmarks = hand_landmarks.landmark

    if len(landmarks) < 21:
        return False

    wrist = landmarks[0]
    fingertips = [4, 8, 12, 16, 20]

    for tip_idx in fingertips:
        tip = landmarks[tip_idx]
        dist = ((tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2) ** 0.5
        if dist > 0.15:
            return False

    return True


@app.get("/")
async def get_frontend():
    """Отдаём главную страницу"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return FileResponse(str(project_root / "frontend" / "index.html"))


@app.websocket("/ws/{app_type}")
async def websocket_endpoint(websocket: WebSocket, app_type: str):
    """WebSocket для передачи данных в реальном времени"""
    await websocket.accept()
    print(f"Client connected to {app_type}")

    # Инициализация игры для змейки
    if app_type == "snake":
        snake_games[id(websocket)] = SnakeGameWeb()

    # Инициализируем камеру
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        await websocket.close(code=1011, reason="Camera not available")
        return

    try:
        while True:
            # Читаем кадр
            ret, frame = cap.read()
            if not ret:
                break

            # Обрабатываем кадр
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False

            # Детекция рук
            results = hands.process(frame_rgb)
            frame_rgb.flags.writeable = True

            gesture_data = {
                "app": app_type,
                "hands": [],
                "frame": None,
                "snake_data": {}  # ДОБАВИМ ДАННЫЕ ДЛЯ ЗМЕЙКИ
            }

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Рисуем landmarks на кадре
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )

                    # Собираем данные о точках руки
                    landmarks = []
                    for idx, lm in enumerate(hand_landmarks.landmark):
                        landmarks.append({
                            "id": idx,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z
                        })

                    hand_data = {
                        "landmarks": landmarks,
                        "index_finger": landmarks[8] if len(landmarks) > 8 else None,
                        "thumb": landmarks[4] if len(landmarks) > 4 else None
                    }

                    gesture_data["hands"].append(hand_data)

                    # ОБРАБОТКА ДЛЯ ЗМЕЙКИ
                    if app_type == "snake":
                        snake = snake_games.get(id(websocket))
                        if snake:
                            # Определяем жест
                            if detect_fist(hand_landmarks):
                                # Кулак = рестарт
                                snake.reset()
                                gesture_data["snake_data"]["gesture"] = "fist"
                            else:
                                # Определяем направление
                                direction = get_direction_from_hand(hand_landmarks)
                                if direction:
                                    snake.update_direction(direction)
                                    gesture_data["snake_data"]["gesture"] = direction

                            # Обновляем игру
                            snake.update()

                            # Получаем состояние игры
                            game_state = snake.get_state()
                            gesture_data["snake_data"].update(game_state)

            # Конвертируем кадр в base64 для отправки в браузер
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            gesture_data["frame"] = f"data:image/jpeg;base64,{frame_base64}"

            # Отправляем данные клиенту
            await websocket.send_json(gesture_data)

            # Контроль FPS
            await asyncio.sleep(0.033)  # ~30 FPS

    except WebSocketDisconnect:
        print(f"Client disconnected from {app_type}")
    except Exception as e:
        print(f"Error in {app_type}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Освобождаем камеру
        cap.release()
        # Удаляем игру змейки при отключении
        if id(websocket) in snake_games:
            del snake_games[id(websocket)]


@app.websocket("/ws/{app_type}")
async def websocket_endpoint(websocket: WebSocket, app_type: str):
    """WebSocket для передачи данных в реальном времени"""
    await websocket.accept()
    print(f"Client connected to {app_type}")

    # Инициализация игры для змейки
    if app_type == "snake":
        snake_games[id(websocket)] = SnakeGameWeb()
        print(f"Created snake game for client {id(websocket)}")

    # Инициализируем камеру
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"ERROR: Camera not available for {app_type}")
        await websocket.close(code=1011, reason="Camera not available")
        return

    try:
        while True:
            # Читаем кадр
            ret, frame = cap.read()
            if not ret:
                print(f"ERROR: Could not read frame for {app_type}")
                break

            # Обрабатываем кадр
            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False

            # Детекция рук
            results = hands.process(frame_rgb)
            frame_rgb.flags.writeable = True

            gesture_data = {
                "app": app_type,
                "hands": [],
                "frame": None,
                "snake_data": {}  # ВАЖНО: Добавляем snake_data
            }

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Рисуем landmarks на кадре
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )

                    # Собираем данные о точках руки
                    landmarks = []
                    for idx, lm in enumerate(hand_landmarks.landmark):
                        landmarks.append({
                            "id": idx,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z
                        })

                    hand_data = {
                        "landmarks": landmarks,
                        "index_finger": landmarks[8] if len(landmarks) > 8 else None,
                        "thumb": landmarks[4] if len(landmarks) > 4 else None
                    }

                    gesture_data["hands"].append(hand_data)

                    # ОБРАБОТКА ДЛЯ ЗМЕЙКИ
                    if app_type == "snake":
                        snake = snake_games.get(id(websocket))
                        if snake:
                            # Определяем жест
                            if detect_fist(hand_landmarks):
                                # Кулак = рестарт
                                snake.reset()
                                gesture_data["snake_data"]["gesture"] = "fist"
                                print("Snake: FIST detected - resetting game")
                            else:
                                # Определяем направление
                                direction = get_direction_from_hand(hand_landmarks)
                                if direction:
                                    snake.update_direction(direction)
                                    gesture_data["snake_data"]["gesture"] = direction
                                    print(f"Snake: Direction {direction}")

                            # Обновляем игру
                            snake.update()

                            # Получаем состояние игры
                            game_state = snake.get_state()
                            gesture_data["snake_data"].update(game_state)

                            # Отладочный вывод
                            print(
                                f"Snake state: score={game_state['score']}, length={game_state['length']}, game_over={game_state['game_over']}")

            # Конвертируем кадр в base64 для отправки в браузер
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            gesture_data["frame"] = f"data:image/jpeg;base64,{frame_base64}"

            # Отладочный вывод
            if app_type == "snake":
                print(
                    f"Sending snake data: has snake_data={bool(gesture_data['snake_data'])}, has snake={bool(gesture_data['snake_data'].get('snake'))}")

            # Отправляем данные клиенту
            await websocket.send_json(gesture_data)

            # Контроль FPS
            await asyncio.sleep(0.033)  # ~30 FPS

    except WebSocketDisconnect:
        print(f"Client disconnected from {app_type}")
    except Exception as e:
        print(f"Error in {app_type}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Освобождаем камеру
        cap.release()
        # Удаляем игру змейки при отключении
        if id(websocket) in snake_games:
            del snake_games[id(websocket)]
            print(f"Removed snake game for client {id(websocket)}")
@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    hands.close()
    print("Server shutdown complete")