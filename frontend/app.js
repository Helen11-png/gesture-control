class GestureApp {
    constructor() {
        this.debugElement = document.getElementById('debug-info');
        this.ws = null;
        this.currentApp = null;
        this.fps = 0;
        this.frameCount = 0;
        this.lastTime = Date.now();
        this.canvas = document.getElementById('hand-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.snakeCanvas = document.getElementById('snake-canvas');
        this.snakeCtx = this.snakeCanvas?.getContext('2d');
        this.snakeGame = null;

        // Для работы с веб-камерой (оставим, но не будем использовать пока)
        this.videoElement = document.createElement('video');
        this.videoElement.style.display = 'none';
        document.body.appendChild(this.videoElement);

        this.videoCanvas = document.createElement('canvas');
        this.videoCtx = this.videoCanvas.getContext('2d');

        this.isSendingFrames = false;
        this.frameInterval = 100;
        this.lastFrameSent = 0;

        // Для хранения состояния игры с сервера
        this.snakeGameState = null;
        this.snakeRenderLoop = null;

        this.initEventListeners();
        this.updateFPS();
    }

    initEventListeners() {
        // Кнопки запуска приложений
        document.querySelectorAll('.app-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.app-card');
                if (card) {
                    const app = card.dataset.app;
                    this.launchApp(app);
                }
            });
        });

        // Кнопка назад
        document.getElementById('back-btn').addEventListener('click', () => {
            this.closeApp();
        });

        // Кнопки змейки
        const restartBtn = document.getElementById('restart-snake');
        const pauseBtn = document.getElementById('pause-snake');

        if (restartBtn) {
            restartBtn.addEventListener('click', () => {
                if (this.currentApp === 'snake' && this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'reset' }));
                }
            });
        }

        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => {
                if (this.currentApp === 'snake' && this.snakeGame) {
                    this.snakeGame.isPaused = !this.snakeGame.isPaused;
                    const btnText = this.snakeGame.isPaused ?
                        '<i class="fas fa-play"></i> Resume' :
                        '<i class="fas fa-pause"></i> Pause';
                    pauseBtn.innerHTML = btnText;
                }
            });
        }
    }

    async launchApp(appType) {
        console.log(`Launching app: ${appType}`);
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

        const panel = document.getElementById(`${appType}-panel`);
        if (panel) {
            panel.style.display = 'block';
        }

        // Если змейка - запускаем рендер-луп
        if (appType === 'snake' && this.snakeCanvas) {
            this.startSnakeRenderLoop();
        }

        // Подключаемся к WebSocket
        await this.connectWebSocket(appType);
    }

    async connectWebSocket(appType) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${appType}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);
            this.updateConnectionStatus('Connecting...', 'connecting');

            this.ws.onopen = () => {
                this.updateConnectionStatus('Connected', 'connected');
                console.log(`Connected to ${appType} app`);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log(`Received data for ${appType}:`, Object.keys(data));
                    this.processGestureData(data);
                    this.frameCount++;
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error, event.data);
                }
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
        console.log('Processing data:', data);

        // Обновляем видео если есть
        if (data.frame && typeof data.frame === 'string') {
            document.getElementById('video-feed').src = data.frame;
        }

        // Обрабатываем данные в зависимости от приложения
        if (this.currentApp === 'coordinates') {
            this.updateCoordinates(data);
        } else if (this.currentApp === 'cursor') {
            this.updateCursor(data);
        } else if (this.currentApp === 'snake') {
            this.updateSnake(data);
        }

        // Общие обновления
        const handCount = data.hands_count || (data.hands ? data.hands.length : 0);
        this.updateHandCount(handCount);
    }
    updateDebugInfo() {
        if (!this.debugElement) return;

        if (this.currentApp === 'snake' && this.snakeGameState) {
            this.debugElement.style.display = 'block';
            document.getElementById('debug-state').innerHTML = `
                Score: ${this.snakeGameState.score || 0}<br>
                Length: ${this.snakeGameState.length || 0}<br>
                Game Over: ${this.snakeGameState.game_over || false}<br>
                Has snake: ${!!(this.snakeGameState.snake && this.snakeGameState.snake.length)}<br>
                Snake length: ${this.snakeGameState.snake ? this.snakeGameState.snake.length : 0}
            `;
        } else {
            this.debugElement.style.display = 'none';
        }
    }
    updateCoordinates(data) {
        console.log('Updating coordinates with data:', data);

        if (data.hands && data.hands.length > 0) {
            const hand = data.hands[0];

            if (hand.index_finger && hand.thumb) {
                document.getElementById('index-coords').textContent =
                    `X: ${(hand.index_finger.x * 100).toFixed(1)}%, Y: ${(hand.index_finger.y * 100).toFixed(1)}%`;

                document.getElementById('thumb-coords').textContent =
                    `X: ${(hand.thumb.x * 100).toFixed(1)}%, Y: ${(hand.thumb.y * 100).toFixed(1)}%`;

                const dx = hand.index_finger.x - hand.thumb.x;
                const dy = hand.index_finger.y - hand.thumb.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                document.getElementById('finger-distance').textContent = distance.toFixed(3);

                if (hand.landmarks) {
                    this.drawHand(hand.landmarks);
                }
            }
        }
    }

    updateCursor(data) {
        console.log('Updating cursor with data:', data);

        if (data.hands && data.hands.length > 0) {
            const hand = data.hands[0];
            const index = hand.index_finger;

            const screenX = Math.round(index.x * window.screen.width);
            const screenY = Math.round(index.y * window.screen.height);

            document.getElementById('cursor-pos').textContent = `${screenX}, ${screenY}`;

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

    updateSnake(data) {
    console.log('=== SNAKE DATA RECEIVED ===');
    console.log('Full data:', data);
    console.log('Keys in data:', Object.keys(data));
    console.log('Has snake_data?', 'snake_data' in data);
    console.log('Has data?', 'data' in data);
    console.log('Has hands?', 'hands' in data, 'hands length:', data.hands?.length);
    console.log('Has frame?', 'frame' in data);

    // Проверяем несколько возможных форматов данных
    if (data.snake_data && data.snake_data.snake) {
        console.log('Found snake_data.snake:', data.snake_data.snake);
        this.snakeGameState = data.snake_data;
    } else if (data.data && data.data.snake) {
        console.log('Found data.data.snake:', data.data.snake);
        this.snakeGameState = data.data;
    } else if (data.snake) {
        console.log('Found direct snake:', data.snake);
        this.snakeGameState = data;
    } else {
        console.log('NO SNAKE DATA FOUND!');
        // Проверим что есть в data
        for (let key in data) {
            console.log(`${key}:`, typeof data[key], Array.isArray(data[key]) ? `array length ${data[key].length}` : data[key]);
        }
    }

    this.updateSnakeInfo();
    this.updateHandCount(data.hands?.length || 0);
}

    startSnakeRenderLoop() {
        if (this.snakeRenderLoop) {
            cancelAnimationFrame(this.snakeRenderLoop);
        }

        const render = () => {
            if (this.currentApp === 'snake' && this.snakeCtx) {
                this.renderSnakeGame();
            }
            this.snakeRenderLoop = requestAnimationFrame(render);
        };

        render();
    }

    renderSnakeGame() {
        if (!this.snakeCtx || !this.snakeCanvas) return;

        const ctx = this.snakeCtx;
        const canvas = this.snakeCanvas;

        // Очищаем canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Если есть состояние игры от сервера, рисуем его
        if (this.snakeGameState) {
            this.drawSnakeFromState(ctx, this.snakeGameState);
        }
        // Иначе просто фон
        else {
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = '#ffffff';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Waiting for game data...', canvas.width / 2, canvas.height / 2);
        }
    }

    drawSnakeFromState(ctx, state) {
        const gridSize = state.grid_size || 20;

        // Фон
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        // Сетка (опционально)
        ctx.strokeStyle = '#16213e';
        ctx.lineWidth = 0.5;

        for (let x = 0; x <= ctx.canvas.width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, ctx.canvas.height);
            ctx.stroke();
        }

        for (let y = 0; y <= ctx.canvas.height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(ctx.canvas.width, y);
            ctx.stroke();
        }

        // Змейка
        if (state.snake && Array.isArray(state.snake)) {
            console.log('Drawing snake segments:', state.snake.length);

            state.snake.forEach((segment, index) => {
                const isHead = index === 0;
                ctx.fillStyle = isHead ? '#00dbde' : '#00a8a8';

                const x = segment[0] || 0;
                const y = segment[1] || 0;

                // Простой квадрат
                ctx.fillRect(x + 1, y + 1, gridSize - 2, gridSize - 2);

                // Обводка
                ctx.strokeStyle = isHead ? '#00ffff' : '#008888';
                ctx.lineWidth = 1;
                ctx.strokeRect(x + 1, y + 1, gridSize - 2, gridSize - 2);
            });
        } else {
            console.log('No snake array in state:', state);
        }

        // Еда
        if (state.food && Array.isArray(state.food)) {
            const foodX = state.food[0] || 0;
            const foodY = state.food[1] || 0;

            ctx.fillStyle = '#ff4757';
            ctx.beginPath();
            ctx.arc(
                foodX + gridSize / 2,
                foodY + gridSize / 2,
                gridSize / 2 - 2,
                0, Math.PI * 2
            );
            ctx.fill();
        }

        // Счет
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(`Score: ${state.score || 0}`, 10, 20);

        // Скорость
        ctx.fillText(`Speed: ${state.speed || 7}`, 10, 40);

        if (state.game_over) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

            ctx.fillStyle = '#ff4757';
            ctx.font = 'bold 24px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('GAME OVER!', ctx.canvas.width / 2, ctx.canvas.height / 2 - 20);

            ctx.fillStyle = '#ffffff';
            ctx.font = '18px Arial';
            ctx.fillText(`Final Score: ${state.score || 0}`, ctx.canvas.width / 2, ctx.canvas.height / 2 + 20);
            ctx.fillText('Show FIST gesture to restart', ctx.canvas.width / 2, ctx.canvas.height / 2 + 50);
        }
    }

    updateSnakeInfo() {
        if (this.snakeGameState) {
            const scoreElement = document.getElementById('snake-score');
            const lengthElement = document.getElementById('snake-length');
            const speedElement = document.getElementById('snake-speed');

            if (scoreElement) scoreElement.textContent = this.snakeGameState.score || 0;
            if (lengthElement) lengthElement.textContent = this.snakeGameState.length ||
                                                          (this.snakeGameState.snake ? this.snakeGameState.snake.length : 1);
            if (speedElement) speedElement.textContent = this.snakeGameState.speed || 7;

            // Обновляем отладочную информацию
            this.updateDebugInfo();
        }
    }

    drawHand(landmarks) {
        if (!this.ctx || !this.canvas) return;

        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;

        ctx.clearRect(0, 0, width, height);
        ctx.strokeStyle = '#00dbde';
        ctx.lineWidth = 2;

        const connections = [
            [0, 1, 2, 3, 4],
            [0, 5, 6, 7, 8],
            [0, 9, 10, 11, 12],
            [0, 13, 14, 15, 16],
            [0, 17, 18, 19, 20]
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

        landmarks.forEach((point, idx) => {
            const x = point.x * width;
            const y = point.y * height;

            if (idx === 8) {
                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fill();
            } else if (idx === 4) {
                ctx.fillStyle = '#00ff00';
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fill();
            } else if ([0, 5, 9, 13, 17].includes(idx)) {
                ctx.fillStyle = '#ffff00';
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        });
    }

    isFist(landmarks) {
        if (!landmarks || landmarks.length < 21) return false;

        const wrist = landmarks[0];
        const fingertips = [4, 8, 12, 16, 20];

        for (let i of fingertips) {
            const point = landmarks[i];
            const dx = point.x - wrist.x;
            const dy = point.y - wrist.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance > 0.15) {
                return false;
            }
        }

        return true;
    }

    updateHandCount(count) {
        const element = document.getElementById('hand-count');
        if (element) {
            element.textContent = count;
        }
    }

    updateConnectionStatus(text, className) {
        const element = document.getElementById('connection-status');
        if (element) {
            element.textContent = text;
            element.className = className;
        }
    }

    updateFPS() {
        setInterval(() => {
            const now = Date.now();
            const delta = (now - this.lastTime) / 1000;
            this.fps = Math.round(this.frameCount / delta);
            this.frameCount = 0;
            this.lastTime = now;

            const fpsElement = document.getElementById('fps');
            if (fpsElement) {
                fpsElement.textContent = this.fps;
            }
        }, 1000);
    }

    closeApp() {
        // Закрываем WebSocket
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        // Останавливаем рендер-луп змейки
        if (this.snakeRenderLoop) {
            cancelAnimationFrame(this.snakeRenderLoop);
            this.snakeRenderLoop = null;
        }

        this.snakeGame = null;
        this.snakeGameState = null;
        this.currentApp = null;

        // Возвращаемся к меню
        const appSelector = document.querySelector('.app-selector');
        const workspace = document.querySelector('.workspace');

        if (appSelector) appSelector.classList.remove('hidden');
        if (workspace) workspace.classList.add('hidden');

        this.updateConnectionStatus('Disconnected', 'disconnected');
    }
}

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing GestureApp...');
    window.gestureApp = new GestureApp();
});