import uvicorn

if __name__ == "__main__":
    print("Запуск Gesture Control Web Server...")
    print("Откройте в браузере: http://localhost:8000")

    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )