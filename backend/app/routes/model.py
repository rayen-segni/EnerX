from fastapi import APIRouter, Query, HTTPException, status
import requests
import joblib
import time

from model import forecast, news_agent, aggregator


router = APIRouter(prefix="/model", tags=["Model"])

BUNDLE = joblib.load(forecast.BUNDLE_PATH)   # modele charge une seule fois au demarrage
STRICT_RANGE = "1"

# Cache de l'analyse news : evite un appel LLM (payant / quota) a chaque requete /forecast
NEWS_TTL_SECONDS = 900
_news_cache = {"t": 0.0, "value": None}

def cached_news():
    if _news_cache["value"] is None or time.time() - _news_cache["t"] > NEWS_TTL_SECONDS:
        _news_cache["value"] = news_agent.analyze()
        _news_cache["t"] = time.time()
    return _news_cache["value"]


@router.get("/news")
def get_news():
    """Analyse des titres d'actualite -> coefficient news et niveau de risque."""
    return cached_news()


@router.get("/forecast")
def get_forecast(
    lat: float = Query(..., ge=30.0, le=37.6, description="Latitude de la centrale (Tunisie)"),
    lon: float = Query(..., ge=7.4, le=11.7, description="Longitude de la centrale (Tunisie)"),
    capacity_kw: float = Query(10, gt=0, le=10000, description="Puissance de la centrale en kW"),
    days: int = Query(7, ge=1, le=14, description="Nombre de jours de prevision"),
    n_tokens: int = Query(1000, ge=1, description="Nombre de tokens de la centrale"),
    news_coef: float = Query(1.0, ge=0, le=2, description="Coefficient de l'agent news (1 = neutre)"),
    tariff: float | None = Query(None, gt=0, description="Tarif DT/kWh (par defaut : tarif STEG selon la capacite)"),
    use_news: bool = Query(False, description="True = l'agent news calcule le coefficient (ignore news_coef)"),
):
    try:
        payload = forecast.fetch_hourly_forecast(lat, lon, days)
        daily = forecast.hourly_to_daily(payload)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Service meteo indisponible, reessayer plus tard")
    except (KeyError, ValueError):
        raise HTTPException(status_code=502, detail="Reponse meteo inattendue, reessayer plus tard")

    if daily.empty:
        raise HTTPException(status_code=502, detail="Aucun jour complet dans la prevision meteo")

    warnings = forecast.quality_warnings(daily, lat, lon, days)
    if STRICT_RANGE and any(w.startswith("Position hors") for w in warnings):
        raise HTTPException(status_code=422, detail=warnings[0])

    pred = forecast.predict_days(daily, lat, lon, capacity_kw, BUNDLE)
    news = None
    if use_news:
        news = cached_news()
        news_coef = news["news_coef"]
    return aggregator.build_report(pred, lat, lon, capacity_kw, tariff, n_tokens, news_coef, news,
                                    warnings=warnings)



