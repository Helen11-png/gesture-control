from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import mediapipe as mp
import numpy as np
import cv2
import base64
import json
import asyncio

from backend.apps.snake_web import SnakeGameWeb

app = FastAPI()

# MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Храним игры для каждого подключения
snake_games = {}


def process_frame_with_mediapipe(frame_bytes):
    """Обработка кадра через MediaPipe"""
    try:
        # Декодируем base64
        img_data = base64.b64decode(frame_bytes.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return None

        # Зеркальное отображение
        frame = cv2.flip(frame, 1)

        # Конвертируем в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        # Обработка
        results = hands.process(frame_rgb)

        return results
    except Exception as e:
        print(f"Frame processing error: {e}")
        return None


@app.websocket("/ws/{app_type}")
async def websocket_handler(websocket: WebSocket, app_type: str):
    await websocket.accept()

    print(f"Connected to {app_type}")

    # Инициализация игры для змейки
    if app_type == "snake":
        snake_games[id(websocket)] = SnakeGameWeb()

    try:
        while True:
            # Получаем данные от клиента
            data = await websocket.receive_json()

            response = {
                'frame': None,  # Можно отправить обработанный кадр
                'hands_count': 0,
                'data': {}
            }

            # Если клиент отправил кадр
            if 'frame' in data and data['frame']:
                results = process_frame_with_mediapipe(data['frame'])

                if results and results.multi_hand_landmarks:
                    response['hands_count'] = len(results.multi_hand_landmarks)

                    # Берем первую руку
                    hand = results.multi_hand_landmarks[0]

                    if app_type == "coordinates":
                        # Координаты
                        index_tip = hand.landmark[8]
                        thumb_tip = hand.landmark[4]

                        response['data'] = {
                            'index_finger': {
                                'x': index_tip.x,
                                'y': index_tip.y,
                                'z': index_tip.z
                            },
                            'thumb': {
                                'x': thumb_tip.x,
                                'y': thumb_tip.y,
                                'z': thumb_tip.z
                            },
                            'landmarks': [
                                {'x': lm.x, 'y': lm.y, 'z': lm.z}
                                for lm in hand.landmark
                            ]
                        }

                    elif app_type == "snake":
                        # Обработка для змейки
                        snake = snake_games.get(id(websocket))

                        if snake:
                            # Определяем жест
                            landmarks = hand.landmark
                            wrist = landmarks[0]

                            # Проверка на кулак
                            is_fist = True
                            for tip_idx in [4, 8, 12, 16, 20]:
                                tip = landmarks[tip_idx]
                                dist = ((tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2) ** 0.5
                                if dist > 0.15:
                                    is_fist = False
                                    break

                            if is_fist:
                                snake.reset()
                            else:
                                # Определяем направление
                                # Центр ладони
                                palm_x = (landmarks[0].x + landmarks[5].x + landmarks[9].x +
                                          landmarks[13].x + landmarks[17].x) / 5
                                palm_y = (landmarks[0].y + landmarks[5].y + landmarks[9].y +
                                          landmarks[13].y + landmarks[17].y) / 5

                                dx = palm_x - wrist.x
                                dy = palm_y - wrist.y

                                if abs(dx) > abs(dy):
                                    direction = 'right' if dx > 0 else 'left'
                                else:
                                    direction = 'down' if dy > 0 else 'up'

                                snake.update_direction(direction)

                            # Обновляем игру
                            snake.update()

                            # Получаем состояние
                            response['data'] = snake.get_state()

            # Отправляем ответ
            await websocket.send_json(response)

    except WebSocketDisconnect:
        print(f"Client disconnected from {app_type}")
    except Exception as e:
        print(f"WebSocket error in {app_type}: {e}")
    finally:
        # Очистка
        if id(websocket) in snake_games:
            del snake_games[id(websocket)]


# Статические файлы
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def get():
    return HTMLResponse(open("frontend/index.html", "r", encoding="utf-8").read())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)