import argparse
from pathlib import Path

import pandas as pd
from catboost import CatBoostRegressor

from src.preprocessing import FEATURES, prepare_features


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Прогноз цены предложения за м² на новых квартирах."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Путь к входному CSV с характеристиками квартир.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("predictions.csv"),
        help="Путь для сохранения CSV с прогнозами.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/catboost_full.cbm"),
        help="Путь к сохранённой модели CatBoost.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    missing_cols = [col for col in FEATURES if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Во входном файле отсутствуют обязательные столбцы: {missing_cols}")

    X = prepare_features(df)

    model = CatBoostRegressor()
    model.load_model(args.model)

    result = df.copy()
    result["predicted_price_per_m2_rub"] = model.predict(X).round().astype(int)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"Сделан прогноз для {len(result)} строк. Результат сохранён: {args.output}")


if __name__ == "__main__":
    main()