import argparse
import re
from decimal import Decimal
from html import unescape
from pathlib import Path


PROJECTS = {
    "simonovskij-val": "Симоновский Вал",
    "arhitektor": "Архитектор",
}


def plain_text(fragment):
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", fragment)).split())


def read_price(card, css_class, suffix=""):
    spans = re.findall(
        r'<span\b[^>]*\bclass="([^"]*)"[^>]*>([^<]*)</span>', card
    )
    for classes, value in spans:
        if css_class in classes.split():
            match = re.fullmatch(r"([0-9 ]+) ₽" + suffix, plain_text(value))
            if match:
                return int(match[1].replace(" ", ""))
    return None


def parse_project_catalog(html_path, slug):
    project = PROJECTS[slug]
    html = Path(html_path).read_text(encoding="utf-8")
    cards = re.findall(
        rf'<a\b[^>]*\bhref="(/{re.escape(slug)}/flats/\d+)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )
    rows, errors = [], []
    if not cards:
        return rows, ["В снимке не найдено ни одной карточки"]

    for href, card in cards:
        heading = re.search(
            r'<div\b[^>]*class="card-flat\b[^"]*"[^>]*>(.*?)</div>',
            card,
            re.DOTALL,
        )
        title = plain_text(heading[1]) if heading else ""
        body = plain_text(card)
        apartment = re.fullmatch(
            r"(Студия|\d+-комнатная)\s*,\s*(\d+(?:[.,]\d+)?)\s*м²",
            title,
            re.IGNORECASE,
        )
        building = re.search(r"(\d+(?:\.\d+)?)\s+корпус\b", body)
        section = re.search(r"\bсекция\s+(\d+)", body)
        floors = re.search(r"\bэтаж\s+(\d+)\s*/\s*(\d+)", body)
        listing = re.search(r"№\s*(\d+)", body)
        price = read_price(card, "price-text")
        per_m2 = read_price(card, "square-price", " за м²")

        required = {
            "тип и площадь": apartment,
            "корпус": building,
            "секция": section,
            "этаж и этажность": floors,
            "номер": listing,
            "цена": price,
            "цена за м²": per_m2,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            errors.append(f"{href}: не извлечено: {', '.join(missing)}")
            continue

        kind, area = apartment.groups()
        floor, floors_total = map(int, floors.groups())
        rows.append({
            "developer": "ГК ФСК",
            "project": project,
            "project_group": f"ГК ФСК | {project}",
            "building": building[1],
            "section": section[1],
            "listing_number": listing[1],
            "id_quality": "source_listing_id",
            "rooms": 0 if kind.casefold() == "студия" else int(kind.split("-")[0]),
            "area_m2": Decimal(area.replace(",", ".")),
            "floor": floor,
            "floors_total": floors_total,
            "asking_price_rub": price,
            "asking_price_per_m2_rub": per_m2,
            "price_per_m2_kind": "published",
            "original_price_rub": read_price(card, "old-price"),
            "source_kind": "catalog_page",
            "source_url": f"https://fsk.ru/{slug}/flats",
        })

    return rows, errors


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Разбор сохранённого каталога ЖК ФСК")
    cli.add_argument("html_path", type=Path)
    cli.add_argument("slug", choices=PROJECTS)
    args = cli.parse_args()

    rows, errors = parse_project_catalog(args.html_path, args.slug)
    keys = {
        (row["building"], row["section"], row["listing_number"]) for row in rows
    }
    print(f"{PROJECTS[args.slug]}: разобрано={len(rows)}, "
          f"уникальных={len(keys)}, ошибок={len(errors)}")
    if rows:
        print("Первая карточка:", rows[0])
    for error in errors:
        print("ПРОВЕРИТЬ:", error)