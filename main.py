# main.py
import mediapipe as mp
from backend.apps.coordinates import CoordinatesApp
from backend.apps.cursor_monitoring import CursorMonitoringApp


def main():
    # Инициализация MediaPipe
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles  # Добавляем стили

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Для курсора достаточно одной руки
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    # Список доступных приложений
    apps = {
        '1': ("Coordinates", CoordinatesApp),
        '2': ("Cursor Control", CursorMonitoringApp)
    }

    while True:
        print("\n" + "=" * 50)
        print("GESTURE CONTROL SYSTEM")
        print("=" * 50)

        for key, (name, _) in apps.items():
            print(f"{key}. {name}")
        print("0. Exit")
        print("=" * 50)

        choice = input("Select application: ").strip()

        if choice == '0':
            print("Goodbye!")
            break

        if choice in apps:
            app_name, app_class = apps[choice]
            print(f"\nStarting {app_name}...")

            try:
                # Создаём и запускаем приложение
                # Передаём всё необходимое
                app = app_class(hands, mp_hands, mp_drawing)
                app.run()

                print(f"\n{app_name} finished.")
            except Exception as e:
                print(f"Ошибка при запуске {app_name}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Invalid choice. Try again.")

    # Освобождаем ресурсы MediaPipe
    hands.close()
    print("Ресурсы освобождены")


if __name__ == "__main__":
    main()