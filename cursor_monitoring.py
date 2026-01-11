import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math

print("Запуск управления курсором жестами...")

# Импорт MediaPipe
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# Получаем размер экрана
screen_width, screen_height = pyautogui.size()
print(f"Размер экрана: {screen_width}x{screen_height}")

# Настройки камеры
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Ошибка: Не удалось открыть камеру")
    exit()

# Размер кадра камеры
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Размер кадра камеры: {frame_width}x{frame_height}")

# Настройки для распознавания рук
with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Только одна рука для управления
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7) as hands:
    print("Управление курсором активно!")
    print("Инструкции:")
    print("1. Указательный палец - перемещение курсора")
    print("2. Большой и указательный палец вместе - клик")
    print("3. Мизинец и безымянный палец вместе - двойной клик")
    print("4. Показать кулак - перетаскивание")
    print("5. Нажмите 'q' в окне камеры для выхода")

    while True:
        # Читаем кадр
        ret, frame = cap.read()
        if not ret:
            break

        # Зеркальное отображение
        frame = cv2.flip(frame, 1)

        # Конвертируем в RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False

        # Обрабатываем
        results = hands.process(image_rgb)

        image_rgb.flags.writeable = True
        frame = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Рисуем ключевые точки
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

                # Получаем координаты пальцев
                landmarks = hand_landmarks.landmark

                # Координаты кончиков пальцев
                thumb_tip = landmarks[4]  # Большой палец
                index_tip = landmarks[8]  # Указательный палец
                middle_tip = landmarks[12]  # Средний палец
                ring_tip = landmarks[16]  # Безымянный палец
                pinky_tip = landmarks[20]  # Мизинец

                # Преобразуем в пиксели
                height, width, _ = frame.shape
                index_x = int(index_tip.x * width)
                index_y = int(index_tip.y * height)

                # 1. УПРАВЛЕНИЕ КУРСОРОМ
                # Преобразуем координаты указательного пальца в координаты экрана
                cursor_x = np.interp(index_tip.x, [0.1, 0.9], [0, screen_width])
                cursor_y = np.interp(index_tip.y, [0.1, 0.9], [0, screen_height])

                # Ограничиваем координаты экрана
                cursor_x = max(0, min(screen_width - 1, cursor_x))
                cursor_y = max(0, min(screen_height - 1, cursor_y))

                # Перемещаем курсор
                pyautogui.moveTo(cursor_x, cursor_y, duration=0.1)


                # 2. ОПРЕДЕЛЯЕМ ЖЕСТЫ

                # Функция для вычисления расстояния между двумя точками
                def distance(p1, p2):
                    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


                # Клик - большой и указательный пальцы сближены
                thumb_index_dist = distance(thumb_tip, index_tip)

                # Двойной клик - мизинец и безымянный палец сближены
                pinky_ring_dist = distance(pinky_tip, ring_tip)

                # Перетаскивание - кулак (все пальцы сжаты)
                # Проверяем расстояние от кончиков пальцев до основания ладони
                wrist = landmarks[0]  # Запястье
                fingers_to_wrist = [
                    distance(index_tip, wrist),
                    distance(middle_tip, wrist),
                    distance(ring_tip, wrist),
                    distance(pinky_tip, wrist)
                ]

                # Жест клика
                if thumb_index_dist < 0.05:  # Пороговое значение
                    pyautogui.click()
                    cv2.putText(frame, 'CLICK!', (50, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    print("Выполнен клик")

                # Жест двойного клика
                elif pinky_ring_dist < 0.03:
                    pyautogui.doubleClick()
                    cv2.putText(frame, 'DOUBLE CLICK!', (50, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                    print("Выполнен двойной клик")

                # Жест перетаскивания (кулак)
                elif all(dist < 0.1 for dist in fingers_to_wrist):
                    pyautogui.mouseDown()
                    cv2.putText(frame, 'DRAGGING...', (50, 200),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                else:
                    pyautogui.mouseUp()

                # Рисуем точку на указательном пальце
                cv2.circle(frame, (index_x, index_y), 15, (0, 0, 255), -1)
                cv2.putText(frame, f'Cursor: {int(cursor_x)},{int(cursor_y)}',
                            (index_x + 20, index_y - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Отображаем информацию
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

        # Отображаем кадр
        cv2.imshow('Gesture Mouse Control', frame)

        # Выход по Q
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Выход из программы...")
            break

# Освобождаем ресурсы
cap.release()
cv2.destroyAllWindows()
print("Программа завершена")