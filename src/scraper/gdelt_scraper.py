"""
src/scraper/gdelt_scraper.py
Descarga archivos GKG de GDELT v2 y agrega sentimiento por día.
Guarda UN registro por día en MongoDB — no artículos crudos.
"""

import os
import io
import csv

csv.field_size_limit(10 * 1024 * 1024)
import zipfile
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from tqdm import tqdm
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv

load_dotenv()

GDELT_BASE_URL = "http://data.gdeltproject.org/gdeltv2/"
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "financial_sentiment"
COLLECTION_NAME = "sentiment_daily"

FINANCIAL_THEMES = [
    "ECON_",
    "FIN_",
    "MARKET",
    "STOCK",
    "RECESSION",
    "INFLATION",
    "INTEREST_RATE",
    "FEDERAL_RESERVE",
    "CENTRAL_BANK",
    "BANKING",
    "DEBT",
    "DEFICIT",
    "GDP",
    "UNEMPLOYMENT",
    "VOLATILITY",
]

GKG_COLUMNS = [
    "GKGRECORDID",
    "DATE",
    "SourceCollectionIdentifier",
    "SourceCommonName",
    "DocumentIdentifier",
    "Counts",
    "V2Counts",
    "Themes",
    "V2Themes",
    "Locations",
    "V2Locations",
    "Persons",
    "V2Persons",
    "Organizations",
    "V2Organizations",
    "V2Tone",
    "Dates",
    "GCAM",
    "SharingImage",
    "RelatedImages",
    "SocialImageEmbeds",
    "SocialVideoEmbeds",
    "Quotations",
    "AllNames",
    "Amounts",
    "TranslationInfo",
    "Extras",
]


def get_collection():
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    col = db[COLLECTION_NAME]
    col.create_index("date", unique=True)
    return col


def generate_timestamps(start_date, end_date):
    current = start_date.replace(minute=0, second=0, microsecond=0)
    while current <= end_date:
        yield current
        current += timedelta(minutes=15)


def build_url(dt):
    return f"{GDELT_BASE_URL}{dt.strftime('%Y%m%d%H%M%S')}.gkg.csv.zip"


def is_financial(themes):
    if not themes:
        return False
    t = themes.upper()
    return any(th in t for th in FINANCIAL_THEMES)


def parse_tone(v2tone):
    if not v2tone:
        return None
    try:
        p = v2tone.split(",")
        return {
            "tone": float(p[0]) if p[0] else None,
            "positive": float(p[1]) if len(p) > 1 else None,
            "negative": float(p[2]) if len(p) > 2 else None,
            "polarity": float(p[3]) if len(p) > 3 else None,
        }
    except (ValueError, IndexError):
        return None


def download_and_parse(url):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 404:
            return []
        r.raise_for_status()
    except requests.RequestException:
        return []

    tones = []
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            with z.open(z.namelist()[0]) as f:
                reader = csv.reader(
                    io.TextIOWrapper(f, encoding="utf-8", errors="replace"),
                    delimiter="\t",
                )
                for row in reader:
                    if len(row) < 10:
                        continue
                    record = dict(zip(GKG_COLUMNS, row))
                    themes = record.get("Themes", "") or record.get("V2Themes", "")
                    if not is_financial(themes):
                        continue
                    tone = parse_tone(record.get("V2Tone", ""))
                    if tone and tone["tone"] is not None:
                        tones.append(tone)
    except (zipfile.BadZipFile, UnicodeDecodeError, IndexError):
        return []

    return tones


def aggregate_day(tones):
    if not tones:
        return {}

    def mean(lst):
        return sum(lst) / len(lst) if lst else None

    def std(lst):
        if len(lst) < 2:
            return None
        m = mean(lst)
        return (sum((x - m) ** 2 for x in lst) / len(lst)) ** 0.5

    tv = [t["tone"] for t in tones if t["tone"] is not None]
    pv = [t["positive"] for t in tones if t.get("positive") is not None]
    nv = [t["negative"] for t in tones if t.get("negative") is not None]
    pl = [t["polarity"] for t in tones if t.get("polarity") is not None]

    return {
        "article_count": len(tones),
        "tone_mean": round(mean(tv), 6) if tv else None,
        "tone_std": round(std(tv), 6) if tv else None,
        "tone_min": round(min(tv), 6) if tv else None,
        "tone_max": round(max(tv), 6) if tv else None,
        "positive_mean": round(mean(pv), 6) if pv else None,
        "negative_mean": round(mean(nv), 6) if nv else None,
        "polarity_mean": round(mean(pl), 6) if pl else None,
    }


def save_daily_to_mongo(daily_data, collection):
    if not daily_data:
        return 0
    ops = [
        UpdateOne(
            {"date": d},
            {"$set": {**stats, "scraped_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        for d, stats in daily_data.items()
        if stats
    ]
    if not ops:
        return 0
    try:
        result = collection.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count
    except BulkWriteError as e:
        return e.details.get("nUpserted", 0)


def scrape_range(start_date, end_date, verbose=True):
    collection = get_collection()
    timestamps = list(generate_timestamps(start_date, end_date))
    daily_tones = defaultdict(list)
    total_articles = 0
    current_day = None

    iterator = tqdm(timestamps, desc="Scraping GDELT") if verbose else timestamps

    for dt in iterator:
        date_str = dt.strftime("%Y-%m-%d")

        if current_day and date_str != current_day:
            day_stats = {current_day: aggregate_day(daily_tones[current_day])}
            save_daily_to_mongo(day_stats, collection)
            if verbose and isinstance(iterator, tqdm):
                tone = day_stats[current_day].get("tone_mean") or 0
                iterator.set_postfix(
                    {
                        "day": current_day,
                        "articles": total_articles,
                        "tone": round(tone, 3),
                    }
                )

        tones = download_and_parse(build_url(dt))
        daily_tones[date_str].extend(tones)
        total_articles += len(tones)
        current_day = date_str

    if current_day and daily_tones[current_day]:
        save_daily_to_mongo(
            {current_day: aggregate_day(daily_tones[current_day])}, collection
        )

    days = len(daily_tones)
    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "days_processed": days,
        "total_articles_processed": total_articles,
        "avg_articles_per_day": round(total_articles / days) if days else 0,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d").replace(hour=23, minute=45)

    print(f"Scraping GDELT: {args.start} → {args.end}")
    stats = scrape_range(start, end)

    print("\n── Resultado ──────────────────")
    for k, v in stats.items():
        print(f"  {k}: {v}")
