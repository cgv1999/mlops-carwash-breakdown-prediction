import mlflow
import os
from fastapi import FastAPI

app = FastAPI()

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

model = None

@app.on_event("startup")
async def load_model():
    global model
    try:
        model_uri = "models:/breakdown_prediction/Production"
        model = mlflow.pyfunc.load_model(model_uri)
        print("Модель загружена из MLflow")
    except Exception as e:
        print(f"Модель не найдена (загрузится после обучения): {e}")
        model = None

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None
    }

@app.get("/predict/box/{box_id}")
def predict_box(box_id: int):
    if model is None:
        return {"error": "Модель ещё не обучена"}, 503
    
    # Заглушка: в реальности читаем признаки из фича-стора
    # и возвращаем прогноз вероятности поломки
    return {
        "box_id": box_id,
        "breakdown_probability_7d": 0.0,
        "message": "Модель загружена и работает"
    }