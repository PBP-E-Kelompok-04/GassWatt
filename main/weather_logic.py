from datetime import datetime

import requests
from django.core.cache import cache
from django.templatetags.static import static

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WEATHER_FIELDS = (
    "temperature_2m", "relative_humidity_2m", "precipitation", "rain", "weather_code", 
    "is_day", "wind_speed_10m", "cloud_cover", "precipitation_probability", "uv_index",
)
AIR_FIELDS = ("us_aqi", "nitrogen_dioxide", "us_aqi_nitrogen_dioxide")

WMO_CODES = {
    0: ('Cerah', 'img/WeatherIcon/WeatherIcon - 1-22.png', 'img/WeatherIcon/WeatherIcon - 1-25.png'),
    1: ('Sebagian besar cerah', 'img/WeatherIcon/WeatherIcon - 1-39.png', 'img/WeatherIcon/WeatherIcon - 1-40.png'),
    2: ('Cerah berawan', 'img/WeatherIcon/WeatherIcon - 1-39.png', 'img/WeatherIcon/WeatherIcon - 1-40.png'),
    3: ('Berawan', 'img/WeatherIcon/WeatherIcon - 1-32.png', 'img/WeatherIcon/WeatherIcon - 1-32.png'),
    45: ('Berkabut', 'img/WeatherIcon/WeatherIcon - 1-41.png', 'img/WeatherIcon/WeatherIcon - 1-41.png'),
    48: ('Kabut beku', 'img/WeatherIcon/WeatherIcon - 1-41.png', 'img/WeatherIcon/WeatherIcon - 1-41.png'),
    51: ('Gerimis ringan', 'img/WeatherIcon/WeatherIcon - 1-37.png', 'img/WeatherIcon/WeatherIcon - 1-58.png'),
    53: ('Gerimis sedang', 'img/WeatherIcon/WeatherIcon - 1-37.png', 'img/WeatherIcon/WeatherIcon - 1-58.png'),
    55: ('Gerimis lebat', 'img/WeatherIcon/WeatherIcon - 1-38.png', 'img/WeatherIcon/WeatherIcon - 1-59.png'),
    56: ('Gerimis beku ringan', 'img/WeatherIcon/WeatherIcon - 1-65.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    57: ('Gerimis beku lebat', 'img/WeatherIcon/WeatherIcon - 1-65.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    61: ('Hujan ringan', 'img/WeatherIcon/WeatherIcon - 1-37.png', 'img/WeatherIcon/WeatherIcon - 1-58.png'),
    63: ('Hujan sedang', 'img/WeatherIcon/WeatherIcon - 1-38.png', 'img/WeatherIcon/WeatherIcon - 1-59.png'),
    65: ('Hujan lebat', 'img/WeatherIcon/WeatherIcon - 1-43.png', 'img/WeatherIcon/WeatherIcon - 1-61.png'),
    66: ('Hujan beku ringan', 'img/WeatherIcon/WeatherIcon - 1-65.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    67: ('Hujan beku lebat', 'img/WeatherIcon/WeatherIcon - 1-65.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    71: ('Salju ringan', 'img/WeatherIcon/WeatherIcon - 1-35.png', 'img/WeatherIcon/WeatherIcon - 1-56.png'),
    73: ('Salju sedang', 'img/WeatherIcon/WeatherIcon - 1-35.png', 'img/WeatherIcon/WeatherIcon - 1-56.png'),
    75: ('Salju lebat', 'img/WeatherIcon/WeatherIcon - 1-36.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    77: ('Butiran salju', 'img/WeatherIcon/WeatherIcon - 1-35.png', 'img/WeatherIcon/WeatherIcon - 1-56.png'),
    80: ('Hujan sesaat ringan', 'img/WeatherIcon/WeatherIcon - 1-50.png', 'img/WeatherIcon/WeatherIcon - 1-59.png'),
    81: ('Hujan sesaat sedang', 'img/WeatherIcon/WeatherIcon - 1-50.png', 'img/WeatherIcon/WeatherIcon - 1-59.png'),
    82: ('Hujan sesaat lebat', 'img/WeatherIcon/WeatherIcon - 1-43.png', 'img/WeatherIcon/WeatherIcon - 1-61.png'),
    85: ('Hujan salju ringan', 'img/WeatherIcon/WeatherIcon - 1-35.png', 'img/WeatherIcon/WeatherIcon - 1-56.png'),
    86: ('Hujan salju lebat', 'img/WeatherIcon/WeatherIcon - 1-36.png', 'img/WeatherIcon/WeatherIcon - 1-57.png'),
    95: ('Badai petir', 'img/WeatherIcon/WeatherIcon - 1-69.png', 'img/WeatherIcon/WeatherIcon - 1-72.png'),
    96: ('Badai petir dan hujan es ringan', 'img/WeatherIcon/WeatherIcon - 1-69.png', 'img/WeatherIcon/WeatherIcon - 1-72.png'),
    99: ('Badai petir dan hujan es lebat', 'img/WeatherIcon/WeatherIcon - 1-69.png', 'img/WeatherIcon/WeatherIcon - 1-72.png'),
}

RECOMMENDATION_IMAGES = {
    'rec-ac-off': 'img/RecommendationWeather/Group-6.png',
    'rec-ac-optimize': 'img/RecommendationWeather/Group-26.png',
    'rec-air': 'img/WeatherIcon/WeatherIcon - 1-6.png',
    'rec-air-quality': 'img/WeatherIcon/WeatherIcon - 1-41.png',
    'rec-bag': 'img/RecommendationWeather/Group-10.png',
    'rec-bicycle': 'img/RecommendationWeather/Group-9.png',
    'rec-daylight': 'img/RecommendationWeather/Group-4.png',
    'rec-night-light': 'img/WeatherIcon/WeatherIcon - 1-25.png',
    'rec-no2': 'img/RecommendationWeather/Group-8.png',
    'rec-public-transport': 'img/RecommendationWeather/Group-8.png',
    'rec-storm': 'img/WeatherIcon/WeatherIcon - 1-69.png',
    'rec-tumbler': 'img/RecommendationWeather/Group-13.png',
    'rec-forest': 'img/RecommendationWeather/Kebakaran.png',
    'rec-wind-alert': 'img/WeatherIcon/WeatherIcon - 1-6.png',
    'rec-rain-alert': 'img/WeatherIcon/WeatherIcon - 1-43.png',
}

GEOCODING_CACHE_SECONDS = 3600
WEATHER_CACHE_SECONDS = 300
AIR_CACHE_SECONDS = 900

AIR_QUALITY_EMPTY = {
    "aqi": None,
    "aqi_category": None,
    "nitrogen_dioxide": None,
    "no2_unit": "µg/m³",
    "no2_aqi": None,
    "air_quality_time": None,
}

class WeatherServiceError(Exception):
    """Kesalahan dari API eksternal atau respons yang tidak valid."""

def image_url(path):
    return static(path) if path else ""

def parse_wmo_code(code, is_day=1):
    description, day_path, night_path = WMO_CODES.get(
        code,
        ("Kondisi tidak diketahui", "img/WeatherIcon/WeatherIcon - 1-32.png",
         "img/WeatherIcon/WeatherIcon - 1-32.png"),
    )
    return description, image_url(day_path if is_day == 1 else night_path)

METRIC_ICON_FILES = {
    "temp": (5, 4, 3),
    "aqi": (22, 39, 41),
    "no2": (22, 39, 41),
    "humidity": (17, 18, 28),
    "rain": (32, 37, 38, 43),
    "pop": (39, 37, 38),
    "uv": (23, 39, 22),
    "cloud": (22, 39, 32),
    "wind": (6,),
    "observed": (23,),
    "time": (25, 22),
}

def metric_icon(name, level=0):
    number = METRIC_ICON_FILES[name][level]
    return image_url(f"img/WeatherIcon/WeatherIcon - 1-{number}.png")

def icon_when_available(name, value, level=0):
    return metric_icon(name, level) if value is not None else ""

def weather_metric_icons(weather):
    temp = weather.get("temperature")
    humidity = weather.get("humidity")
    rain = weather.get("precipitation")
    pop = weather.get("pop")
    uv = weather.get("uv_index")
    cloud = weather.get("cloud_cover")
    aqi = weather.get("aqi")
    no2 = weather.get("nitrogen_dioxide")
    no2_aqi = weather.get("no2_aqi")
    is_day = weather.get("is_day")

    return {
        "temp": icon_when_available("temp", temp,
            2 if temp is not None and temp > 31 else 1 if temp is not None and temp >= 26 else 0),
        "humidity": icon_when_available("humidity", humidity,
            2 if humidity is not None and humidity > 85 else 1 if humidity is not None and humidity >= 40 else 0),
        "rain": icon_when_available("rain", rain,
            0 if rain == 0 else 3 if rain is not None and rain >= 2.5
            else 2 if rain is not None and rain >= 1 else 1),
        "pop": icon_when_available("pop", pop,
            2 if pop is not None and pop > 70 else 1 if pop is not None and pop >= 20 else 0),
        "uv": icon_when_available("uv", uv,
            2 if uv is not None and uv >= 6 else 1 if uv is not None and uv >= 3 else 0),
        "cloud": icon_when_available("cloud", cloud,
            2 if cloud is not None and cloud >= 70 else 1 if cloud is not None and cloud >= 20 else 0),
        "wind": icon_when_available("wind", weather.get("wind_speed")),
        "aqi": icon_when_available("aqi", aqi,
            2 if aqi is not None and aqi > 100 else 1 if aqi is not None and aqi > 50 else 0),
        "no2": icon_when_available("no2", no2,
            2 if no2_aqi is not None and no2_aqi > 100
            else 1 if no2_aqi is None or no2_aqi > 50 else 0),
        "code": weather.get("weather_icon") if weather.get("weather_code") is not None else "",
        "time": metric_icon("time", 1 if is_day == 1 else 0) if is_day in (0, 1) else "",
        "observed": icon_when_available("observed", weather.get("observed_at")),
    }

def api_get(url, params):
    try:
        response = requests.get(url, params=params, timeout=(3, 8))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error"):
            raise WeatherServiceError("API mengembalikan data tidak valid.")
        return payload
    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError("Layanan Open-Meteo sedang tidak tersedia.") from exc

def cached(cache_key, timeout, fetcher):
    data = cache.get(cache_key)
    if data is not None:
        return data
    data = fetcher()
    cache.set(cache_key, data, timeout=timeout)
    return data

def search_locations(query):
    normalized = query.strip()
    cache_key = "geo:" + normalized.casefold()

    def fetch():
        payload = api_get(GEOCODING_URL, {
            "name": normalized, "count": 7, "language": "id", "format": "json",
        })
        results = []
        for item in payload.get("results", []):
            if item.get("latitude") is None or item.get("longitude") is None:
                continue
            parts = [item.get("name"), item.get("admin1"), item.get("country")]
            unique_parts = []
            for part in parts:
                if part and part not in unique_parts:
                    unique_parts.append(part)
            results.append({
                "name": ", ".join(unique_parts),
                "latitude": item["latitude"],
                "longitude": item["longitude"],
            })
        return results

    return cached(cache_key, GEOCODING_CACHE_SECONDS, fetch)

def aqi_category(aqi):
    if aqi is None:
        return None
    elif aqi <= 50:
        return "Baik"
    elif aqi <= 100:
        return "Sedang"
    elif aqi <= 150:
        return "Tidak sehat bagi kelompok sensitif"
    elif aqi <= 200:
        return "Tidak sehat"
    elif aqi <= 300:
        return "Sangat tidak sehat"
    return "Berbahaya"

def get_air_quality(latitude, longitude):
    cache_key = f"air:{latitude:.4f}:{longitude:.4f}"

    def fetch():
        payload = api_get(AIR_QUALITY_URL, {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(AIR_FIELDS),
            "timezone": "auto",
        })
        current = payload.get("current")
        if not isinstance(current, dict) or not current.get("time"):
            raise WeatherServiceError("Respons kualitas udara tidak memiliki data terkini.")

        units = payload.get("current_units") or {}
        result = {
            "aqi": current.get("us_aqi"),
            "aqi_category": aqi_category(current.get("us_aqi")),
            "nitrogen_dioxide": current.get("nitrogen_dioxide"),
            "no2_unit": units.get("nitrogen_dioxide", "µg/m³"),
            "no2_aqi": current.get("us_aqi_nitrogen_dioxide"),
            "air_quality_time": current.get("time"),
        }
        if result["aqi"] is None and result["nitrogen_dioxide"] is None:
            raise WeatherServiceError("AQI dan NO₂ tidak tersedia untuk lokasi ini.")
        return result

    return cached(cache_key, AIR_CACHE_SECONDS, fetch)

def parse_forecast(payload):
    current = payload.get("current")
    if not isinstance(current, dict) or any(
        current.get(key) is None for key in ("time", "temperature_2m", "weather_code", "is_day")
    ):
        raise WeatherServiceError("Respons cuaca tidak memiliki data saat ini.")

    time_str = current["time"]
    try:
        datetime.fromisoformat(time_str)
    except (ValueError, TypeError) as exc:
        raise WeatherServiceError("Waktu data cuaca tidak valid.") from exc

    description, icon_url = parse_wmo_code(current["weather_code"], current["is_day"])
    return {
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "rain": current.get("rain"),
        "pop": current.get("precipitation_probability"),
        "wind_speed": current.get("wind_speed_10m"),
        "cloud_cover": current.get("cloud_cover"),
        "weather_code": current["weather_code"],
        "weather_desc": description,
        "weather_icon": icon_url,
        "is_day": current["is_day"],
        "day_period": "Siang" if current["is_day"] == 1 else "Malam",
        "uv_index": current.get("uv_index"),
        "observed_at": time_str,
        "timezone": payload.get("timezone", ""),
    }


def get_weather(latitude, longitude):
    cache_key = f"forecast:{latitude:.4f}:{longitude:.4f}"

    def fetch():
        payload = api_get(FORECAST_URL, {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(WEATHER_FIELDS),
            "forecast_days": 1,
            "timezone": "auto",
        })
        weather = parse_forecast(payload)
        try:
            weather.update(get_air_quality(latitude, longitude))
        except WeatherServiceError:
            weather.update(AIR_QUALITY_EMPTY.copy())

        weather["icons"] = weather_metric_icons(weather)
        weather["recommendations"] = generate_recommendations(weather)
        return weather

    return cached(cache_key, WEATHER_CACHE_SECONDS, fetch)

def rec(title, desc, icon_key):
    return {
        "title": title,
        "desc": desc,
        "icon": image_url(RECOMMENDATION_IMAGES[icon_key]),
    }

def air_is_unhealthy(weather):
    return any(
        value is not None and value > 100
        for value in (weather.get("aqi"), weather.get("no2_aqi"))
    )

def energy_recommendations(weather):
    temp = weather.get("temperature")
    rain = weather.get("precipitation")
    is_day = weather.get("is_day")
    code = weather.get("weather_code")
    air_unhealthy = air_is_unhealthy(weather)
    items = []

    if temp <= 25:
        if air_unhealthy:
            items.append(rec(
                "Hemat AC tanpa membuka jendela",
                f"Suhu luar sejuk ({temp:g}°C), tetapi kualitas udara kurang baik. "
                "Gunakan kipas atau sirkulasi udara dalam ruangan, hindari membuka "
                "jendela saat polusi sedang tinggi.",
                "rec-air"
            ))
        else:
            items.append(rec(
                "Kurangi penggunaan AC",
                f"Suhu luar cukup sejuk ({temp:g}°C). Bila kualitas udara di luar "
                "baik dan kondisi aman, matikan AC dan buka jendela atau gunakan kipas.",
                "rec-ac-off"
            ))
    elif temp <= 30:
        items.append(rec(
            "Optimalkan pengaturan AC",
            f"Suhu luar sedang panas ({temp:g}°C). Jika ingin menggunakan AC, "
            "coba atur 25°C dan tutup pintu/jendela agar pendinginan efisien.",
            "rec-ac-optimize"
        ))
    else:
        items.append(rec(
            "Optimalkan pengaturan AC dan kipas",
            f"Suhu luar sedang panas ({temp:g}°C). Jika ingin menggunakan AC, "
            "coba atur 25°C, boleh memakai kipas, dan tutup pintu/jendela agar pendinginan efisien.",
            "rec-ac-optimize"
        ))

    if is_day == 1 and temp >= 28 and rain == 0:
        items.append(rec(
            "Manfaatkan panas matahari",
            f"Hari sedang siang dan  Suhu luar sedang panas ({temp:g}°C)."
            "Manfaatkanlah cahaya matahari untuk menjemur pakaian.",
            "rec-daylight"
        ))

    if is_day == 1 and code is not None and code <= 2:
        items.append(rec(
            "Gunakan cahaya alami",
            "Matahari cukup cerah. Buka tirai dan matikan lampu "
            "yang tidak dibutuhkan.",
            "rec-daylight"
        ))
    elif is_day == 0:
        items.append(rec(
            "Hemat pencahayaan malam",
            "Gunakan lampu seperlunya dan matikan lampu di ruang kosong.",
            "rec-night-light"
        ))
    return items

def mobility_recommendations(weather):
    code = weather.get("weather_code")
    pop = weather.get("pop")
    rain = weather.get("precipitation")
    wind = weather.get("wind_speed")
    aqi = weather.get("aqi")
    air_unhealthy = air_is_unhealthy(weather)
    temp = weather.get("temperature")
    uv = weather.get("uv_index")
    is_day = weather.get("is_day")
    items = []

    if code in (95, 96, 99):
        items.append(rec(
            "Tunda perjalanan saat badai",
            "Ada indikasi badai petir. Utamakan keselamatan dan "
            "tunda perjalanan jika memungkinkan.",
            "rec-storm"
        ))
    elif air_unhealthy:
        items.append(rec(
            "Batasi paparan polusi saat bepergian",
            f"Kualitas udara kurang baik ({aqi}). "
            "Hindari olahraga berat dekat jalan raya dan pertimbangkan transportasi "
            "umum jika perlu bepergian.",
            "rec-public-transport"
        ))

    if pop is not None and 40 <= pop <= 70:
        items.append(rec(
            "Persiapan menghadapi hujan",
            f"Hujan berpeluang turun sebesar {pop}%. Direkomendasikan "
            "untuk membawa payung atau jas hujan jika ingin berpergian",
            "rec-rain-alert"
        ))
    elif (pop is not None and pop > 70) or (rain is not None and rain > 0):
        items.append(rec(
            "Prioritaskan transportasi umum",
            "Potensi hujan tinggi atau sedang hujan. Jika harus pergi "
            "dan kondisi aman, pertimbangkan naik transportasi umum daripada kendaraan pribadi.",
            "rec-public-transport"
        ))

    if (code is not None and 0 <= code <= 3
            and pop is not None and pop < 20
            and wind is not None and wind < 30
            and (rain is None or rain == 0)
            and aqi is not None and aqi <= 100
            and not air_unhealthy):
        items.append(rec(
            "Jalan kaki atau bersepeda",
            "Cuaca mendukung! Untuk perjalanan dekat, berjalan "
            "kaki atau bersepeda sangat direkomendasikan ",
            "rec-bicycle"
        ))

    if wind is not None and wind >= 30:
        items.append(rec(
            "Waspadai angin kencang",
            f"Angin sekitar {wind:g} km/jam. Hindari bersepeda di jalan "
            "terbuka apabila angin terasa sangat kencang.",
            "rec-wind-alert"
        ))

    if is_day == 1 and temp >= 32 and uv is not None and uv >= 6:
        items.append(rec(
            "Cuaca sedang panas",
            "Jika ingin berpergian disarankan memilih rute yang teduh "
            "dan memakai sunscreen.",
            "rec-daylight"
        ))
    return items

def other_recommendations(weather):
    temp = weather.get("temperature")
    aqi = weather.get("aqi")
    no2 = weather.get("nitrogen_dioxide")
    no2_aqi = weather.get("no2_aqi")
    is_day = weather.get("is_day")
    items = []

    if temp > 30:
        items.append(rec(
            "Bawa tumbler sendiri",
            "Suhu luar cukup panas. Bawa botol minum isi ulang agar "
            "tidak perlu membeli air kemasan plastik sekali pakai.",
            "rec-tumbler"
        ))

        if is_day == 1:
            items.append(rec(
                "Cuaca sedang panas",
                "Suhu luar cukup panas. Hindari meninggalkan barang yang "
                "mudah terbakar di luar ruangan",
                "rec-daylight"
            ))

    if aqi is not None and aqi > 150:
        items.append(rec(
            "Kurangi aktivitas di luar ruangan",
            f"Kualitas udara sebesar {aqi} ({aqi_category(aqi)}). Batasi aktivitas luar yang berat, "
            "khususnya bagi kelompok rentan.",
            "rec-air-quality"
        ))
        items.append(rec(
            "Hindari membakar sembarangan",
            f"Kualitas udara sebesar {aqi} ({aqi_category(aqi)}). Jangan membakar atau membuang benda mudah "
            "terbakar sembarangan.",
            "rec-forest"
        ))
    elif aqi is not None and aqi > 100:
        items.append(rec(
            "Waspadai kualitas udara",
            f"Kualitas udara sebesar {aqi} ({aqi_category(aqi)}). Kelompok sensitif sebaiknya "
            "mengurangi aktivitas berat dan lama di luar ruangan. Direkomendasikan memakai masker.",
            "rec-air-quality"
        ))
    elif aqi is not None and aqi > 50:
        items.append(rec(
            "Perhatikan kualitas udara sedang",
            f"Kualitas udara sebesar {aqi} ({aqi_category(aqi)}). Orang yang sangat sensitif terhadap "
            "polusi harus berhati-hati.",
            "rec-air-quality"
        ))

    if no2 is not None or no2_aqi is not None:
        concentration = (
            f"Estimasi NO₂ {no2:g} {weather.get('no2_unit') or 'µg/m³'}. "
            if no2 is not None else ""
        )
        if no2_aqi is not None and no2_aqi > 100:
            text = (concentration + f"Subindeks NO₂ {no2_aqi}. "
                    "Kurangi aktivitas dekat jalan ramai dan pilih rute dengan "
                    "paparan polusi kendaraan lebih rendah.")
            title = "Waspadai paparan NO₂"
        else:
            text = (concentration + "Kurangi mesin kendaraan menyala saat berhenti "
                    "dan pertimbangkan transportasi umum untuk menekan emisi NO₂.")
            title = "Kurangi sumber emisi NO₂"
        items.append(rec(title, text, "rec-no2"))

    items.append(rec(
        "Kurangi kemasan sekali pakai",
        "Bawa tas belanja pakai ulang dan pilih produk dengan kemasan "
        "seminimal mungkin.",
        "rec-bag"
    ))
    return items

def generate_recommendations(weather):
    return {
        "energi": energy_recommendations(weather),
        "mobilitas": mobility_recommendations(weather),
        "lainnya": other_recommendations(weather),
    }