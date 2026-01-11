import cv2
import mediapipe as mp
import numpy as np

print(f"MediaPipe версия: {mp.__version__}")
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# Инициализируем камеру
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Ошибка: Не удалось открыть камеру")
    exit()

print("Камера успешно открыта")

# Настройки для распознавания рук
with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as hands:
    print("Начинаем отслеживание рук...")

    while True:
        # Читаем кадр с камеры
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр")
            break

        # Зеркальное отображение (для естественного восприятия)
        frame = cv2.flip(frame, 1)

        # Конвертируем BGR в RGB (MediaPipe работает с RGB)
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Улучшаем производительность
        image_rgb.flags.writeable = False

        # Обрабатываем изображение
        results = hands.process(image_rgb)

        # Возвращаем возможность записи
        image_rgb.flags.writeable = True

        # Если найдены руки
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Рисуем ключевые точки и соединения
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

                # Получаем координаты кончика указательного пальца (индекс 8)
                index_finger_tip = hand_landmarks.landmark[8]

                # Преобразуем нормализованные координаты в пиксели
                height, width, _ = frame.shape
                x_pixel = int(index_finger_tip.x * width)
                y_pixel = int(index_finger_tip.y * height)

                # Рисуем красную точку на кончике пальца
                cv2.circle(frame, (x_pixel, y_pixel), 10, (0, 0, 255), -1)

                # Отображаем координаты
                cv2.putText(frame, f'X:{x_pixel}, Y:{y_pixel}',
                            (x_pixel + 15, y_pixel - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                # Можно также вывести в консоль
                # print(f"Координаты: X={x_pixel}, Y={y_pixel}")

        # Добавляем информацию на экран
        cv2.putText(frame, 'Hand Tracking - MediaPipe', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, 'Press Q to quit', (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Отображаем результат
        cv2.imshow('Hand Tracking', frame)

        # Выход по нажатию Q
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Завершение программы...")
            break

# Освобождаем ресурсы
cap.release()
cv2.destroyAllWindows()
print("Программа завершена")