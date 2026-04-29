# Financial Sentiment Project

## Descripción
Sistema de análisis de sentimiento financiero que cruza datos de noticias de GDELT v2 con el índice VIX, almacenados en MongoDB, para modelar y predecir sentimiento de mercado.

## Fuentes de datos
- GDELT v2 GKG: archivos cada 15 min desde data.gdeltproject.org/gdeltv2/
- VIX: índice de volatilidad via yfinance (^VIX, desde 2016)
- MongoDB: base de datos principal (DB: financial_sentiment)

## Colecciones MongoDB
- `sentiment_daily`: un registro por día con métricas agregadas de tono
  - tone_mean, tone_std, tone_min, tone_max
  - positive_mean, negative_mean, polarity_mean
  - article_count, scraped_at
- `vix`: datos históricos del VIX (vix_close)

## Filtrado GDELT
Solo se procesan artículos con temas financieros:
ECON_, FIN_, MARKET, STOCK, RECESSION, INFLATION,
INTEREST_RATE, FEDERAL_RESERVE, BANKING, DEBT, GDP, etc.

## Estructura del proyecto
- `src/scraper/gdelt_scraper.py` — scraper principal GDELT
- `notebooks/` — exploración (VIX + MongoDB implementado)
- `data/` — datos raw y procesados
- `outputs/` — modelos exportados y resultados
- `logs/` — logs de ejecución
- `config/` — configuración y parámetros
- `.env` — MONGODB_URI y credenciales

## Stack técnico
- Python 3.11, pymongo, yfinance
- pandas, numpy, requests, tqdm
- ML: por definir (XGBoost, LightGBM, FinBERT candidatos)

## Convenciones
- Credenciales siempre en .env, nunca hardcodeadas
- Datos raw nunca se modifican
- Modelos entrenados se guardan en outputs/models/
- El scraper usa upsert — se puede relanzar sin duplicados

## Subagentes disponibles
- `eda-analyst` — exploración de sentiment_daily y VIX en MongoDB
- `feature-engineer` — features sobre series temporales y métricas de tono
- `model-trainer` — entrenamiento de modelos predictivos
- `model-evaluator` — métricas, curvas ROC/PR, SHAP
- `scraper-agent` — ejecución y monitoreo del scraper GDELT
- `report-writer` — generación de informes y documentación
