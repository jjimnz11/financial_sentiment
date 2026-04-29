# Financial Sentiment — NLP Crisis Predictor

> **Research question:** Can financial news sentiment predict market movements 24–48 hours in advance?

Extension of my Master's thesis (TFM) — adding NLP sentiment analysis as additional features to an LSTM-based financial crisis early warning system.

## Project structure

```
financial_sentiment/
│
├── config/
│   └── config.yaml          # Toda la configuración centralizada
│
├── data/
│   ├── raw/                 # Headlines crudos (JSON por fuente y día)
│   ├── processed/           # Series temporales de sentimiento (Parquet)
│   └── cache/               # SQLite cache para no re-scrapear
│
├── src/
│   ├── scraper/             # Módulo 1: recolección de titulares
│   │   ├── rss_scraper.py   # Reuters, FT, WSJ vía RSS
│   │   ├── newsapi_client.py
│   │   └── alpha_vantage_client.py
│   │
│   ├── nlp/                 # Módulo 2: análisis de sentimiento
│   │   ├── finbert_model.py # FinBERT (modelo principal)
│   │   ├── vader_model.py   # VADER (baseline)
│   │   └── aggregator.py    # Ventanas 24h / 48h
│   │
│   ├── features/            # Módulo 3: feature engineering
│   │   ├── sentiment_features.py
│   │   └── merger.py        # Une features TFM + sentimiento
│   │
│   ├── model/               # Módulo 4: LSTM
│   │   ├── lstm_builder.py  # Arquitectura (del TFM)
│   │   ├── trainer.py       # Training loop + ablation study
│   │   └── evaluator.py     # AUC, precision, recall, backtesting
│   │
│   └── utils/
│       ├── config_loader.py
│       ├── logger.py
│       └── storage.py       # Helpers para Parquet / SQLite
│
├── notebooks/
│   ├── 00_exploration.ipynb       # EDA de titulares
│   ├── 01_sentiment_analysis.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_ablation_study.ipynb    # Comparativa con/sin sentimiento
│
├── outputs/
│   ├── figures/             # Gráficos para el post/paper
│   └── reports/             # Métricas de experimentos
│
├── tests/
│   ├── test_scraper.py
│   └── test_nlp.py
│
├── .env.example             # Template de API keys
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Clonar y entrar al directorio
git clone <repo>
cd financial_sentiment

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API keys
cp .env.example .env
# Editar .env con tus claves

# 5. Verificar configuración
python -c "from src.utils.config_loader import load_config; print(load_config()['project'])"
```

## Fuentes de datos

| Fuente | Tipo | Plan gratuito | Noticias/día |
|--------|------|---------------|--------------|
| Reuters RSS | RSS | Sí, sin límite | ~50–100 |
| Financial Times RSS | RSS | Sí, sin límite | ~30–50 |
| WSJ RSS | RSS | Sí, sin límite | ~20–40 |
| NewsAPI | API | 100 req/día | ~500 |
| Alpha Vantage | API | 25 req/día | ~50 |

## Modelos de sentimiento

- **FinBERT** (`ProsusAI/finbert`) — modelo principal, preentrenado en texto financiero
- **VADER** — baseline rápido sin GPU, para comparación

## Experimentos (ablation study)

| Experimento | Features | Objetivo |
|-------------|----------|----------|
| Baseline | 40 indicadores técnicos (TFM) | Reproducir TFM (val AUC ~0.70) |
| + Sentimiento 24h | Base + EWM 24h | ¿Mejora el AUC? |
| + Sentimiento 48h | Base + EWM 48h | ¿Qué ventana es mejor? |
| + All sentiment | Base + 24h + 48h + volumen | Impacto completo |

## Referencia TFM

- Modelo: LSTM early warning system
- Target: crisis binaria (VIX > 25 + divergencia NASDAQ/Gold)
- Datos: NASDAQ/Gold 2005–2025 (diario)
- Resultado base: val AUC = 0.7001, test AUC = 0.5421

## Publicación objetivo

> *"I added NLP sentiment analysis to my LSTM crisis detection system — here's what changed."*

Post LinkedIn + repositorio GitHub documentado.
