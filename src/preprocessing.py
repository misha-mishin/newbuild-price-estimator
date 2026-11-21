import pandas as pd

FEATURES = ["developer", "rooms", "area_m2", "floor"]
CAT_FEATURES = ["developer"]
TARGET = "asking_price_per_m2_rub"


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Отбирает признаки модели и приводит типы к формату CatBoost."""
    X = df[FEATURES].copy()
    
    # Пропуски в застройщике заменяем на явную категорию, числовые NaN CatBoost обрабатывает сам
    X["developer"] = X["developer"].fillna("Не указано").astype(str)
    for col in ["rooms", "area_m2", "floor"]:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    return X