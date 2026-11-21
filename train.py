import argparse
from pathlib import Path

import pandas as pd
from catboost import CatBoostRegressor

from src.preprocessing import CAT_FEATURES, TARGET, prepare_features

SEED = 42
MODEL_PARAMS = {
    "depth": 3,
    "learning_rate": 0.18661212048851333,
    "iterations": 15,
    "loss_function": "MAE",
    "random_seed": SEED,
    "verbose": False,
    "allow_writing_files": False,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучение финальной модели CatBoost.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/processed/newbuild_prices_clean.csv"),
        help="Путь к очищенному датасету.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/catboost_full.cbm"),
        help="Путь для сохранения модели.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    X = prepare_features(df)
    y = df[TARGET]

    model = CatBoostRegressor(**MODEL_PARAMS)
    model.fit(X, y, cat_features=CAT_FEATURES)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(args.output)
    print(f"Обучено на {len(df)} строках. Модель сохранена: {args.output}")


if __name__ == "__main__":
    main()