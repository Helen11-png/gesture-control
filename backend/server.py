# backend/server.py
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


@app.get("/")
async def get_frontend():
    """Отдаём главную страницу"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        # Если index.html не найден, показываем простую страницу
        return FileResponse(str(project_root / "frontend" / "index.html"))


@app.websocket("/ws/{app_type}")
async def websocket_endpoint(websocket: WebSocket, app_type: str):
    """WebSocket для передачи данных в реальном времени"""
    await websocket.accept()
    print(f"Client connected to {app_type}")

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
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False

            # Детекция рук
            results = hands.process(frame_rgb)

            frame_rgb.flags.writeable = True

            gesture_data = {
                "app": app_type,
                "hands": [],
                "frame": None
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

                    gesture_data["hands"].append({
                        "landmarks": landmarks,
                        "index_finger": landmarks[8] if len(landmarks) > 8 else None,
                        "thumb": landmarks[4] if len(landmarks) > 4 else None
                    })

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


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при завершении"""
    hands.close()
    print("Server shutdown complete")