# apps/base_app.py - Базовый класс для всех приложений
from abc import ABC, abstractmethod
# apps/base_app.py - убедитесь, что это есть
import cv2

class BaseGestureApp(ABC):
    """Абстрактный базовый класс для приложений управления жестами"""

    def __init__(self, hands, mp_hands, mp_drawing):
        self.hands = hands
        self.mp_hands = mp_hands
        self.mp_drawing = mp_drawing
        self.cap = None

    @abstractmethod
    def process_frame(self, frame, hand_landmarks):
        """Обработка одного кадра. Возвращает обработанный кадр."""
        pass

    def setup(self):
        """Настройка приложения (опционально)"""
        self.cap = cv2.VideoCapture(0)
        return True

    def cleanup(self):
        """Очистка ресурсов приложения"""
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def run(self):
        """Основной цикл приложения"""
        if not self.setup():
            return

        print(f"Запущено приложение: {self.__class__.__name__}")
        print("Нажмите 'q' для выхода")

        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                print("Не удалось получить кадр с камеры")
                break

            # Зеркальное отображение для естественного восприятия
            frame = cv2.flip(frame, 1)

            # Конвертация цвета для MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)

            # Обработка результатов
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Рисуем landmarks
                    self.mp_drawing.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                    # Обрабатываем кадр в дочернем классе
                    frame = self.process_frame(frame, hand_landmarks)

            # Показываем FPS
            cv2.putText(frame, "Press 'q' to quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Отображаем результат
            cv2.imshow('Gesture Control', frame)

            # Выход по нажатию 'q'
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

        self.cleanup()
        cv2.destroyAllWindows()