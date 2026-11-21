
import { useState } from "react";
import {
  Leaf,
  MapPin,
  Sprout,
  Droplets,
  ArrowRight,
} from "lucide-react";
import "./App.css";

function App() {
  const [zipCode, setZipCode] = useState("");
  const [crop, setCrop] = useState("Corn");
  const [soil, setSoil] = useState("I don't know");
  const [stage, setStage] = useState("Growing");

  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setWeather(null);

    try {
      const params = new URLSearchParams({
        zip: zipCode,
        crop: crop,
        soil: soil,
        stage: stage,
      });

      const response = await fetch(
        `http://127.0.0.1:5000/api/weather?${params.toString()}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
      }

      setWeather(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="dashboard">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Leaf size={23} />
          </div>
          <div>
            <h2>ClimateIQ</h2>
            <span>Agricultural intelligence</span>
          </div>
        </div>

        <span className="prototype-label">
          Prototype environment
        </span>
      </header>

      <main className="main-content">
        <section className="welcome">
          <p className="eyebrow">YOUR FARM, INFORMED BY DATA</p>
          <h1>Make smarter decisions for your farm.</h1>
          <p>
            Access local weather insights, irrigation guidance,
            and growing recommendations using public environmental data.
          </p>
        </section>

        <section className="farm-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">GET STARTED</span>
              <h2>Tell us about your farm</h2>
              <p>
                We'll use this information to generate
                recommendations for your location and crops.
              </p>
            </div>
            <div className="section-icon">
              <Sprout size={25} />
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>
                <MapPin size={16} /> Farm ZIP code
              </label>
              <input
                type="text"
                placeholder="e.g. 08816"
                value={zipCode}
                onChange={(event) => setZipCode(event.target.value)}
                pattern="[0-9]{5}"
                maxLength="5"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>
                  <Sprout size={16} /> Main crop
                </label>
                <select
                  value={crop}
                  onChange={(event) => setCrop(event.target.value)}
                >
                  <option>Corn</option>
                  <option>Soybeans</option>
                  <option>Wheat</option>
                  <option>Tomatoes</option>
                  <option>Potatoes</option>
                  <option>Blueberries</option>
                  <option>Other</option>
                </select>
              </div>

              <div className="form-group">
                <label>
                  <Droplets size={16} /> Soil type
                </label>
                <select
                  value={soil}
                  onChange={(event) => setSoil(event.target.value)}
                >
                  <option>I don't know</option>
                  <option>Sandy</option>
                  <option>Loamy</option>
                  <option>Clay</option>
                  <option>Silty</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Crop growth stage</label>
              <select
                value={stage}
                onChange={(event) => setStage(event.target.value)}
              >
                <option>Planting</option>
                <option>Growing</option>
                <option>Flowering</option>
                <option>Fruiting</option>
                <option>Harvesting</option>
              </select>
            </div>

            <button
              type="submit"
              className="submit-button"
              disabled={loading}
            >
              {loading ? "Retrieving weather..." : "Create my farm profile"}
              <ArrowRight size={18} />
            </button>
          </form>
        </section>

        {weather && (
          <section className="farm-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">LIVE WEATHER DATA</span>
                <h2>
                  {weather.location.city}, {weather.location.state}
                </h2>
                <p>
                  Weather information for ZIP code {weather.location.zip}
                </p>
              </div>
              <div className="section-icon">
                <Droplets size={25} />
              </div>
            </div>

            <div className="weather-grid">
              <div className="weather-card">
                <span>Temperature</span>
                <h3>{weather.weather.temperature}°F</h3>

                <div className="irrigation-panel">
                  <div className="irrigation-heading">
                    <Droplets size={22} />
                    <h3>Smart Irrigation Advisor</h3>
                  </div>

                  <p className="irrigation-recommendation">
                    {weather.irrigation.recommendation}
                  </p>

                  <div className="irrigation-stats">
                    <div>
                      <span>Estimated daily water demand</span>
                      <strong>
                        {weather.irrigation.estimated_crop_water_demand_mm_day !== null
                          ? `${weather.irrigation.estimated_crop_water_demand_mm_day} mm/day`
                          : "Unavailable"}
                      </strong>
                    </div>

                    <div>
                      <span>Reference ET₀</span>
                      <strong>
                        {weather.irrigation.et0_mm_day !== null
                          ? `${weather.irrigation.et0_mm_day} mm/day`
                          : "Unavailable"}
                      </strong>
                    </div>
                  </div>

                  <p className="irrigation-note">
                    <strong>Soil guidance:</strong>{" "}
                    {weather.irrigation.soil_note}
                  </p>

                  <p className="irrigation-note">
                    <strong>Growth-stage guidance:</strong>{" "}
                    {weather.irrigation.stage_note}
                  </p>

                  <p className="irrigation-confidence">
                    Data confidence: {weather.irrigation.confidence}
                  </p>
                </div>
              </div>

              <div className="weather-card">
                <span>Humidity</span>
                <h3>{weather.weather.humidity}%</h3>
              </div>

              <div className="weather-card">
                <span>Precipitation</span>
                <h3>{weather.weather.precipitation} mm</h3>
              </div>
            </div>

            <div className="alerts-panel">
              <div className="alerts-heading">
                <h3>Environmental Risk Alerts</h3>
                <span>7-day forecast analysis</span>
              </div>

              <div className="alerts-list">
                {weather.alerts?.map((alert, index) => (
                  <div
                    className={`alert-card ${alert.level.toLowerCase()}`}
                    key={index}
                  >
                    <div className="alert-card-heading">
                      <strong>{alert.type}</strong>
                      <span>{alert.level} Risk</span>
                    </div>

                    <p>{alert.message}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="soil-panel">
              <div className="soil-heading">
                <div>
                  <h3>Soil Moisture Insights</h3>
                  <span>
                    Estimated moisture at different soil depths
                  </span>
                </div>
                <Droplets size={23} />
              </div>

              <div className="soil-layers">
                <div className="soil-layer">
                  <div className="soil-layer-info">
                    <strong>Surface</strong>
                    <span>3–9 cm depth</span>
                  </div>
                  <strong>
                    {weather.soil_moisture?.surface != null
                      ? weather.soil_moisture.surface.toFixed(3)
                      : "Unavailable"}
                  </strong>
                </div>

                <div className="soil-layer">
                  <div className="soil-layer-info">
                    <strong>Shallow root zone</strong>
                    <span>9–27 cm depth</span>
                  </div>
                  <strong>
                    {weather.soil_moisture?.shallow_root_zone != null
                      ? weather.soil_moisture.shallow_root_zone.toFixed(3)
                      : "Unavailable"}
                  </strong>
                </div>

                <div className="soil-layer">
                  <div className="soil-layer-info">
                    <strong>Deep root zone</strong>
                    <span>27–81 cm depth</span>
                  </div>
                  <strong>
                    {weather.soil_moisture?.deep_root_zone != null
                      ? weather.soil_moisture.deep_root_zone.toFixed(3)
                      : "Unavailable"}
                  </strong>
                </div>
              </div>

              <p className="soil-units">
                Values in m³/m³ (volumetric water content)
              </p>

              <p className="soil-disclaimer">
                These are model-derived estimates from Open-Meteo, not direct
                measurements from sensors in your field. Use them as an
                additional insight when assessing soil conditions.
              </p>
            </div>

            <p className="weather-source">
              Weather data provided by {weather.source}
            </p>
          </section>
        )}

        {loading && (
          <p>Retrieving local weather data...</p>
        )}

        {error && (
          <p className="error-message">{error}</p>
        )}

        <footer className="page-footer">
          ClimateIQ · Helping farmers make data-informed decisions.
        </footer>
      </main>
    </div>
  );
}

export default App;
