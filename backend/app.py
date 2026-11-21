
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


@app.route("/")
def home():
    return jsonify({"message": "ClimateIQ API is running"})


@app.route("/api/weather")
def get_weather():
    zip_code = request.args.get("zip", "").strip()
    crop = request.args.get("crop", "Other")
    soil = request.args.get("soil", "I don't know")
    stage = request.args.get("stage", "Growing")

    if not re.fullmatch(r"\d{5}", zip_code):
        return jsonify({
            "error": "Please provide a valid 5-digit US ZIP code."
        }), 400

    try:
        # 1. Geocode ZIP code
        geo_response = requests.get(
            GEOCODING_URL,
            params={
                "name": zip_code,
                "count": 10,
                "language": "en",
                "format": "json"
            },
            timeout=15
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        results = geo_data.get("results", [])

        location_result = next(
            (
                item for item in results
                if item.get("country_code") == "US"
                and item.get("feature_code") == "PPL"
            ),
            None
        )

        if not location_result:
            location_result = next(
                (
                    item for item in results
                    if item.get("country_code") == "US"
                ),
                None
            )

        if not location_result:
            return jsonify({
                "error": "Could not find that ZIP code. Please check it and try again."
            }), 404

        latitude = location_result["latitude"]
        longitude = location_result["longitude"]
        city = location_result.get("name", "Unknown")
        state = location_result.get("admin1", "Unknown")

        # 2. Retrieve weather and soil-moisture data
        weather_response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_sum,"
                    "et0_fao_evapotranspiration"
                ),
                "hourly": (
                    "soil_moisture_3_to_9cm,"
                    "soil_moisture_9_to_27cm,"
                    "soil_moisture_27_to_81cm"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "mm",
                "timezone": "auto",
                "forecast_days": 7
            },
            timeout=20
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})
        hourly = weather_data.get("hourly", {})

        current_units = weather_data.get("current_units", {})
        daily_units = weather_data.get("daily_units", {})
        hourly_units = weather_data.get("hourly_units", {})

        # 3. Extract soil-moisture readings
        hourly_times = hourly.get("time", [])
        current_time = current.get("time")

        soil_index = None

        if current_time and hourly_times:
            try:
                current_datetime = datetime.fromisoformat(current_time)
                parsed_times = [
                    datetime.fromisoformat(t) for t in hourly_times
                ]

                soil_index = min(
                    range(len(parsed_times)),
                    key=lambda i: abs(
                        (parsed_times[i] - current_datetime).total_seconds()
                    )
                )
            except (ValueError, TypeError):
                soil_index = None

        def get_soil_value(parameter):
            values = hourly.get(parameter, [])

            if soil_index is not None and soil_index < len(values):
                return values[soil_index]

            return None

        soil_moisture = {
            "surface": get_soil_value("soil_moisture_3_to_9cm"),
            "shallow_root_zone": get_soil_value("soil_moisture_9_to_27cm"),
            "deep_root_zone": get_soil_value("soil_moisture_27_to_81cm"),
            "units": hourly_units.get(
                "soil_moisture_3_to_9cm", "m³/m³"
            ),
            "timestamp": (
                hourly_times[soil_index]
                if soil_index is not None
                else None
            )
        }

        # 4. Weather descriptions
        weather_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail"
        }

        weather_code = current.get("weather_code")
        description = weather_descriptions.get(
            weather_code,
            "Weather conditions unavailable"
        )

        # 5. Estimate crop water demand
        et0_values = daily.get("et0_fao_evapotranspiration", [])
        rain_values = daily.get("precipitation_sum", [])

        et0 = et0_values[0] if et0_values else None
        rain = rain_values[0] if rain_values else None

        crop_kc = {
            "Corn": 1.15,
            "Soybeans": 1.10,
            "Wheat": 1.15,
            "Tomatoes": 1.15,
            "Potatoes": 1.10,
            "Blueberries": 0.90,
            "Other": 1.00
        }

        stage_factor = {
            "Planting": 0.50,
            "Growing": 0.85,
            "Flowering": 1.15,
            "Fruiting": 1.10,
            "Harvesting": 0.50
        }

        base_kc = crop_kc.get(crop, 1.00)
        growth_factor = stage_factor.get(stage, 1.00)
        kc = round(base_kc * growth_factor, 2)

        if et0 is not None:
            crop_demand = round(et0 * kc, 2)
        else:
            crop_demand = None

        # 6. Soil-specific guidance
        soil_notes = {
            "Sandy": "Sandy soil drains quickly and holds less water.",
            "Loamy": "Loamy soil generally balances drainage and water retention.",
            "Clay": "Clay soil retains water longer and may drain slowly.",
            "Silty": "Silty soil can retain substantial moisture.",
            "I don't know": "Soil type is unknown, so water retention cannot be estimated."
        }

        soil_note = soil_notes.get(
            soil,
            soil_notes["I don't know"]
        )

        if soil == "Sandy":
            soil_action = (
                "Check root-zone moisture frequently because water "
                "may drain away quickly."
            )
        elif soil == "Clay":
            soil_action = (
                "Check soil moisture and drainage before irrigating "
                "to avoid waterlogging."
            )
        elif soil == "Silty":
            soil_action = (
                "Check soil moisture and drainage before adding more water."
            )
        elif soil == "Loamy":
            soil_action = "Check root-zone moisture before irrigating."
        else:
            soil_action = (
                "Inspect the soil directly before deciding whether to irrigate."
            )

        # 7. Irrigation recommendation
        if crop_demand is None:
            recommendation = (
                "Water-demand data is unavailable. "
                "Check soil moisture before deciding to irrigate."
            )
        elif rain is not None and rain >= 3:
            recommendation = (
                "Forecast rainfall may help meet crop water needs. "
                "Check field conditions before irrigating."
            )
        elif crop_demand >= 4.5:
            recommendation = (
                "Estimated crop water demand is relatively high. "
                "Inspect root-zone moisture and consider irrigation "
                "if the soil is dry."
            )
        else:
            recommendation = (
                "Current estimated crop water demand is relatively low. "
                "Continue monitoring soil moisture before irrigating."
            )

        recommendation += " " + soil_action

        if stage == "Flowering":
            recommendation += (
                " Flowering can be sensitive to water stress, "
                "so monitor moisture closely."
            )

        # 8. Growth-stage guidance
        if stage == "Flowering":
            stage_note = (
                "Flowering can be sensitive to water stress. "
                "Monitor moisture closely."
            )
        elif stage == "Planting":
            stage_note = (
                "Keep the seed zone adequately moist to support "
                "germination and establishment."
            )
        elif stage == "Growing":
            stage_note = (
                "Monitor soil moisture as the crop develops "
                "and water demand changes."
            )
        elif stage == "Fruiting":
            stage_note = (
                "Maintain consistent soil moisture while the crop "
                "develops its fruit."
            )
        elif stage == "Harvesting":
            stage_note = (
                "Avoid unnecessary irrigation near harvest and "
                "consider crop-specific harvesting needs."
            )
        else:
            stage_note = (
                "Recommendations account for the selected growth stage."
            )

        # 9. Seven-day forecast
        forecast = []

        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precipitation = daily.get("precipitation_sum", [])
        et0_forecast = daily.get("et0_fao_evapotranspiration", [])

        for i in range(len(dates)):
            forecast.append({
                "date": dates[i],
                "max_temp": max_temps[i] if i < len(max_temps) else None,
                "min_temp": min_temps[i] if i < len(min_temps) else None,
                "precipitation": (
                    precipitation[i] if i < len(precipitation) else None
                ),
                "et0": (
                    et0_forecast[i] if i < len(et0_forecast) else None
                )
            })

        # 10. Environmental risk alerts
        alerts = []

        if min_temps and min_temps[0] is not None:
            if min_temps[0] <= 32:
                alerts.append({
                    "type": "Frost Risk",
                    "level": "High",
                    "message": (
                        "Forecast temperatures may reach freezing. "
                        "Assess crop sensitivity and consider protective measures."
                    )
                })

        if rain is not None and rain >= 20:
            alerts.append({
                "type": "Heavy Rainfall",
                "level": "High",
                "message": (
                    "Significant rainfall is forecast. Check drainage "
                    "and watch for waterlogging or runoff."
                )
            })

        if (
            crop_demand is not None
            and crop_demand >= 4.5
            and (rain is None or rain < 1)
        ):
            alerts.append({
                "type": "Potential Water Stress",
                "level": "Moderate",
                "message": (
                    "Estimated crop water demand is relatively high "
                    "while little rainfall is forecast. Check soil moisture."
                )
            })

        if not alerts:
            alerts.append({
                "type": "No Major Weather Alerts",
                "level": "Low",
                "message": (
                    "No major risks were identified from the available "
                    "weather forecast. Continue monitoring local conditions."
                )
            })

        # 11. Return data to frontend
        return jsonify({
            "location": {
                "zip": zip_code,
                "city": city,
                "state": state,
                "latitude": latitude,
                "longitude": longitude
            },

            "weather": {
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "feels_like": current.get("apparent_temperature"),
                "precipitation": current.get("precipitation"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": weather_code,
                "description": description
            },

            "units": {
                "temperature": current_units.get("temperature_2m", "°F"),
                "humidity": current_units.get("relative_humidity_2m", "%"),
                "feels_like": current_units.get("apparent_temperature", "°F"),
                "precipitation": current_units.get("precipitation", "mm"),
                "wind_speed": current_units.get("wind_speed_10m", "mph")
            },

            "forecast": forecast,

            "forecast_units": {
                "temperature": daily_units.get("temperature_2m_max", "°F"),
                "precipitation": daily_units.get("precipitation_sum", "mm"),
                "et0": daily_units.get("et0_fao_evapotranspiration", "mm")
            },

            "farm_profile": {
                "crop": crop,
                "soil": soil,
                "stage": stage
            },

            "irrigation": {
                "et0_mm_day": et0,
                "kc": kc,
                "estimated_crop_water_demand_mm_day": crop_demand,
                "rain_mm": rain,
                "recommendation": recommendation,
                "soil_note": soil_note,
                "stage_note": stage_note,
                "confidence": (
                    "Moderate - weather-based estimate, not a field measurement"
                )
            },

            "soil_moisture": soil_moisture,

            "alerts": alerts,

            "source": "Open-Meteo"
        })

    except requests.exceptions.RequestException as error:
        return jsonify({
            "error": "Unable to retrieve weather data. Please try again.",
            "details": str(error)
        }), 502

    except Exception as error:
        return jsonify({
            "error": "An unexpected server error occurred.",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )
