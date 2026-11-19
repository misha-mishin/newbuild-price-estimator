import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from parse_fsk_project import parse_project_catalog


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "data/raw/newbuild_prices.csv"
OUTPUT = ROOT / "data/collected/newbuild_prices_fsk_projects.csv"
SLUGS = ("simonovskij-val", "arhitektor")


def apartment_key(row):
    fields = ("developer", "project", "building", "listing_number")
    return tuple(" ".join(str(row[field]).split()).casefold() for field in fields)


def section(row):
    return str(row["section"] or "").strip()


def number(value):
    text = str(value or "").strip().replace(",", ".")
    return Decimal(text) if text else None


def same_apartment(old, new):
    return (
        section(old) == section(new)
        and number(old["floor"]) == number(new["floor"])
        and number(old["area_m2"]) == number(new["area_m2"])
    )


def validate_apartment(row):
    problems = []

    if row["area_m2"] <= 0:
        problems.append("площадь должна быть больше нуля")

    if row["asking_price_rub"] <= 0:
        problems.append("цена предложения должна быть больше нуля")

    if row["asking_price_per_m2_rub"] <= 0:
        problems.append("цена за м² должна быть больше нуля")

    if not 1 <= row["floor"] <= row["floors_total"]:
        problems.append("этаж должен быть от 1 до общего числа этажей")

    original_price = row["original_price_rub"]
    if original_price is not None and original_price <= row["asking_price_rub"]:
        problems.append("цена до скидки должна быть выше цены предложения")

    return problems


def main():
    parser = argparse.ArgumentParser(description="Сбор квартир из двух каталогов ФСК")
    parser.add_argument("snapshots", type=Path, help="Папка с двумя HTML-снимками")
    parser.add_argument("retrieved_on", type=date.fromisoformat, help="Дата снимков: ГГГГ-ММ-ДД")
    args = parser.parse_args()

    original = defaultdict(list)
    with ORIGINAL.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        for row in reader:
            original[apartment_key(row)].append(row)

    seen = {}
    counts = Counter()
    issues = []

    for slug in SLUGS:
        rows, errors = parse_project_catalog(args.snapshots / f"{slug}.html", slug)
        counts["прочитано"] += len(rows)
        issues.extend(f"{slug}: {error}" for error in errors)

        for row in rows:
            key = apartment_key(row)

            problems = validate_apartment(row)
            if problems:
                issues.append(f"{key}: {'; '.join(problems)}")
                continue
            candidates = original.get(key, [])
            if any(same_apartment(old, row) for old in candidates):
                counts["дубли с исходным"] += 1
                continue
            if candidates:
                issues.append(f"{key}: совпали ЖК, корпус и номер, но различаются характеристики")
                continue

            full_key = (*key, section(row))
            previous = seen.get(full_key)
            if previous is not None:
                if previous != row:
                    issues.append(f"{full_key}: повтор карточки с разными данными")
                else:
                    counts["повторы в сборе"] += 1
                continue
            if abs(row["asking_price_rub"] / row["area_m2"] / row["asking_price_per_m2_rub"] - 1) > 0.025:
                issues.append(f"{key}: цена, площадь и цена за м² не сходятся")

            seen[full_key] = row

    print(
        f"Прочитано: {counts['прочитано']} | "
        f"Дубли с исходным: {counts['дубли с исходным']} | "
        f"Повторы в сборе: {counts['повторы в сборе']} | "
        f"Новых: {len(seen)} | Ошибок и спорных случаев: {len(issues)}"
    )
    if issues:
        raise SystemExit("CSV не записан:\n" + "\n".join(issues))
    if len(seen) < 30:
        raise SystemExit(f"CSV не записан: найдено {len(seen)} новых строк, нужно не менее 30.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with OUTPUT.open("x", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for index, row in enumerate(seen.values(), start=1):
                original_price = row["original_price_rub"]
                discount = round(100 * (1 - row["asking_price_rub"] / original_price)) if original_price else None
                export = {
                    **row,
                    "record_id": f"FSK-NEW-{args.retrieved_on:%Y%m%d}-{index:04d}",
                    "discount_pct": discount,
                    "retrieved_on": args.retrieved_on.isoformat(),
                }
                writer.writerow({column: export.get(column) for column in columns})
    except FileExistsError:
        raise SystemExit(f"Файл уже существует, перезапись отменена: {OUTPUT}")

    print("Новые по ЖК:", dict(Counter(row["project"] for row in seen.values())))
    print(f"Сохранено: {len(seen)} строк, {len(columns)} столбца → {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()