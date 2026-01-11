class GestureApp {
    constructor() {
        this.ws = null;
        this.currentApp = null;
        this.fps = 0;
        this.frameCount = 0;
        this.lastTime = Date.now();
        this.canvas = document.getElementById('hand-canvas');
        this.ctx = this.canvas.getContext('2d');

        this.initEventListeners();
        this.updateFPS();
    }

    initEventListeners() {
        // Кнопки запуска приложений
        document.querySelectorAll('.app-btn').forEach(btn => {
            if (!btn.disabled) {
                btn.addEventListener('click', (e) => {
                    const app = e.target.closest('.app-card').dataset.app;
                    this.launchApp(app);
                });
            }
        });

        // Кнопка назад
        document.getElementById('back-btn').addEventListener('click', () => {
            this.closeApp();
        });
    }

    async launchApp(appType) {
        this.currentApp = appType;

        // Обновляем интерфейс
        document.querySelector('.app-selector').classList.add('hidden');
        document.querySelector('.workspace').classList.remove('hidden');
        document.getElementById('current-app').textContent =
            appType.charAt(0).toUpperCase() + appType.slice(1);

        // Показываем соответствующую панель
        document.querySelectorAll('.data-container').forEach(panel => {
            panel.style.display = 'none';
        });
        document.getElementById(`${appType}-panel`).style.display = 'block';

        // Подключаемся к WebSocket
        await this.connectWebSocket(appType);
    }

    async connectWebSocket(appType) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${appType}`;

        try {
            this.ws = new WebSocket(wsUrl);
            this.updateConnectionStatus('Connecting...', 'connecting');

            this.ws.onopen = () => {
                this.updateConnectionStatus('Connected', 'connected');
                console.log(`Connected to ${appType} app`);
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.processGestureData(data);
                this.frameCount++;
            };

            this.ws.onclose = () => {
                this.updateConnectionStatus('Disconnected', 'disconnected');
                console.log('WebSocket disconnected');
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('Error', 'error');
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            alert('Failed to connect to server. Make sure backend is running.');
        }
    }

    processGestureData(data) {
        // Обновляем видео
        if (data.frame) {
            document.getElementById('video-feed').src = data.frame;
        }

        // Обрабатываем данные в зависимости от приложения
        if (this.currentApp === 'coordinates') {
            this.updateCoordinates(data);
        } else if (this.currentApp === 'cursor') {
            this.updateCursor(data);
        }

        // Общие обновления
        this.updateHandCount(data.hands?.length || 0);
    }

    updateCoordinates(data) {
        if (data.hands && data.hands.length > 0) {
            const hand = data.hands[0];

            // Отображаем координаты
            document.getElementById('index-coords').textContent =
                `X: ${(hand.index_finger.x * 100).toFixed(1)}%, Y: ${(hand.index_finger.y * 100).toFixed(1)}%`;

            document.getElementById('thumb-coords').textContent =
                `X: ${(hand.thumb.x * 100).toFixed(1)}%, Y: ${(hand.thumb.y * 100).toFixed(1)}%`;

            // Рассчитываем расстояние
            const dx = hand.index_finger.x - hand.thumb.x;
            const dy = hand.index_finger.y - hand.thumb.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            document.getElementById('finger-distance').textContent = distance.toFixed(3);

            // Рисуем схему руки
            this.drawHand(hand.landmarks);
        }
    }

    updateCursor(data) {
        if (data.hands && data.hands.length > 0) {
            const hand = data.hands[0];
            const index = hand.index_finger;

            // Преобразуем координаты в экранные
            const screenX = Math.round(index.x * window.screen.width);
            const screenY = Math.round(index.y * window.screen.height);

            // Обновляем позицию курсора
            document.getElementById('cursor-pos').textContent =
                `${screenX}, ${screenY}`;

            // Определяем жест
            const dx = hand.index_finger.x - hand.thumb.x;
            const dy = hand.index_finger.y - hand.thumb.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            let gesture = "Moving";
            if (distance < 0.05) {
                gesture = "Click";
            } else if (this.isFist(hand.landmarks)) {
                gesture = "Drag";
            }

            document.getElementById('current-gesture').textContent = gesture;
        }
    }

    drawHand(landmarks) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Очищаем канвас
        ctx.clearRect(0, 0, width, height);

        // Рисуем связи
        ctx.strokeStyle = '#00dbde';
        ctx.lineWidth = 2;

        // Соединения пальцев (упрощённо)
        const connections = [
            [0, 1, 2, 3, 4],     // Большой палец
            [0, 5, 6, 7, 8],     // Указательный
            [0, 9, 10, 11, 12],  // Средний
            [0, 13, 14, 15, 16], // Безымянный
            [0, 17, 18, 19, 20]  // Мизинец
        ];

        connections.forEach(finger => {
            ctx.beginPath();
            finger.forEach((pointIdx, i) => {
                const point = landmarks[pointIdx];
                const x = point.x * width;
                const y = point.y * height;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.stroke();
        });

        // Рисуем точки
        landmarks.forEach((point, idx) => {
            const x = point.x * width;
            const y = point.y * height;

            // Разные цвета для разных типов точек
            if (idx === 8) {
                ctx.fillStyle = '#ff0000'; // Указательный палец - красный
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fill();
            } else if (idx === 4) {
                ctx.fillStyle = '#00ff00'; // Большой палец - зеленый
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fill();
            } else if ([0, 5, 9, 13, 17].includes(idx)) {
                ctx.fillStyle = '#ffff00'; // Основания пальцев - желтый
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        });
    }

    isFist(landmarks) {
        // Простая проверка на кулак (все пальцы близко к запястью)
        const wrist = landmarks[0];
        let allClose = true;

        // Проверяем кончики пальцев
        for (let i of [4, 8, 12, 16, 20]) {
            const point = landmarks[i];
            const dx = point.x - wrist.x;
            const dy = point.y - wrist.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance > 0.15) { // Пороговое значение
                allClose = false;
                break;
            }
        }

        return allClose;
    }

    updateHandCount(count) {
        document.getElementById('hand-count').textContent = count;
    }

    updateConnectionStatus(text, className) {
        const element = document.getElementById('connection-status');
        element.textContent = text;
        element.className = className;
    }

    updateFPS() {
        setInterval(() => {
            const now = Date.now();
            const delta = (now - this.lastTime) / 1000;
            this.fps = Math.round(this.frameCount / delta);
            this.frameCount = 0;
            this.lastTime = now;

            document.getElementById('fps').textContent = this.fps;
        }, 1000);
    }

    closeApp() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.currentApp = null;

        // Возвращаемся к меню
        document.querySelector('.app-selector').classList.remove('hidden');
        document.querySelector('.workspace').classList.add('hidden');
        this.updateConnectionStatus('Disconnected', 'disconnected');
    }
}

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => {
    window.gestureApp = new GestureApp();
});