import { useCallback, useEffect, useState } from "react";
import ClimateMap from "../components/ClimateMap.jsx";
import "./Dashboard.css";

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8010"
).replace(/\/$/, "");

const navigation = [
  { label: "Dashboard", icon: "◫", page: "dashboard" },
  { label: "Rainfall Analytics", icon: "⌁", page: "rainfall" },
  { label: "Weather Insights", icon: "☀", page: "insights" },
  { label: "Forecast", icon: "↗", page: "forecast" },
  { label: "AI Climate Assistant", icon: "✳", page: "assistant" },
];

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

async function requestJson(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : payload?.message || response.statusText;
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return payload;
}

function formatValue(value, suffix = "", digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    return `${value.toLocaleString(undefined, {
      maximumFractionDigits: digits,
    })}${suffix}`;
  }
  return `${value}${suffix}`;
}

function WeatherTable({ records, loading }) {
  if (loading) {
    return <div className="ci-empty-state">Loading weather observations…</div>;
  }

  if (!records.length) {
    return (
      <div className="ci-empty-state">
        <strong>No weather observations are available.</strong>
        <p>Check that the backend dataset is available.</p>
      </div>
    );
  }

  return (
    <div className="ci-table-scroll">
      <table className="ci-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Mean temperature</th>
            <th>Rainfall</th>
            <th>Humidity</th>
            <th>Wind speed</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={record.time || index}>
              <td>{record.time || "—"}</td>
              <td>{formatValue(record["temperature_2m_mean (°C)"], " °C")}</td>
              <td>{formatValue(record["precipitation_sum (mm)"], " mm")}</td>
              <td>
                {formatValue(record["relative_humidity_2m_mean (%)"], "%")}
              </td>
              <td>{formatValue(record["wind_speed_10m_max (km/h)"], " km/h")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MonthlyRainfall({ records, loading }) {
  if (loading) {
    return <div className="ci-empty-state">Loading monthly rainfall…</div>;
  }

  if (!records.length) {
    return (
      <div className="ci-empty-state">
        <strong>Monthly rainfall data is unavailable.</strong>
        <p>Check the backend endpoint at <code>/weather/monthly-rainfall</code>.</p>
      </div>
    );
  }

  const values = records.map((record) => record.average_rainfall_mm);
  const maxValue = Math.max(...values, 0);

  return (
    <>
      <div className="ci-rainfall-chart" aria-label="Average rainfall by month">
        {records.map((record) => {
          const value = Number(record.average_rainfall_mm) || 0;
          const height = maxValue > 0 ? Math.max((value / maxValue) * 100, 2) : 2;

          return (
            <div className="ci-rainfall-chart__column" key={record.month}>
              <strong>{formatValue(value, "", 1)}</strong>
              <div className="ci-rainfall-chart__track">
                <span style={{ height: `${height}%` }} />
              </div>
              <span>{months[record.month - 1]?.slice(0, 3) || record.month}</span>
            </div>
          );
        })}
      </div>
      <p className="ci-chart-caption">
        Mean daily precipitation for each calendar month, in millimetres.
      </p>
    </>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [rainfall, setRainfall] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState({});
  const [menuOpen, setMenuOpen] = useState(false);
  const [activePage, setActivePage] = useState("dashboard");
  const [question, setQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState(null);
  const [indexError, setIndexError] = useState("");

  const loadDashboard = useCallback(async (signal) => {
    setLoading(true);
    setLoadErrors({});

    const endpoints = [
      ["summary", "/weather/summary"],
      ["recent", "/weather/recent?limit=7"],
      ["rainfall", "/weather/monthly-rainfall"],
      ["forecast", "/forecast/latest"],
    ];
    const results = await Promise.allSettled(
      endpoints.map(([, path]) => requestJson(path, { signal }))
    );

    if (signal?.aborted) return;

    const nextErrors = {};
    results.forEach((result, index) => {
      const [key] = endpoints[index];
      if (result.status === "rejected") {
        nextErrors[key] = result.reason.message;
        return;
      }

      switch (key) {
        case "summary":
          setSummary(result.value);
          break;
        case "recent":
          setRecent(Array.isArray(result.value) ? result.value : []);
          break;
        case "rainfall":
          setRainfall(Array.isArray(result.value) ? result.value : []);
          break;
        case "forecast":
          setForecast(result.value);
          break;
        default:
          break;
      }
    });

    setLoadErrors(nextErrors);
    setLoading(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadDashboard(controller.signal);
    return () => controller.abort();
  }, [loadDashboard]);

  function navigate(page) {
    setActivePage(page);
    setMenuOpen(false);
  }

  async function submitQuestion(event) {
    event.preventDefault();
    const prompt = question.trim();
    if (!prompt || chatLoading) return;

    setChatMessages((messages) => [...messages, { role: "user", content: prompt }]);
    setQuestion("");
    setChatLoading(true);
    setChatError("");

    try {
      const result = await requestJson("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: prompt }),
      });
      setChatMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          content: result.answer || "The assistant returned no answer.",
          sources: Array.isArray(result.sources) ? result.sources : [],
        },
      ]);
    } catch (error) {
      setChatError(error.message);
    } finally {
      setChatLoading(false);
    }
  }

  async function indexDocuments() {
    setIndexing(true);
    setIndexError("");
    setIndexResult(null);

    try {
      setIndexResult(await requestJson("/rag/index", { method: "POST" }));
    } catch (error) {
      setIndexError(error.message);
    } finally {
      setIndexing(false);
    }
  }

  const activeLabel =
    navigation.find((item) => item.page === activePage)?.label || "Dashboard";
  const metricCards = [
    {
      label: "Historical records",
      value: summary ? formatValue(summary.records, "", 0) : "—",
      foot: summary ? `${summary.start_date} to ${summary.end_date}` : "Weather dataset",
      icon: "▤",
      tone: "teal",
    },
    {
      label: "Average daily rainfall",
      value: summary
        ? formatValue(summary.average_daily_rainfall_mm, " mm", 2)
        : "—",
      foot: "Across the full observation period",
      icon: "⌁",
      tone: "blue",
    },
    {
      label: "Rainy days",
      value: summary ? formatValue(summary.rainy_days, "", 0) : "—",
      foot: "Days with measured precipitation",
      icon: "☂",
      tone: "purple",
    },
    {
      label: "Total rainfall",
      value: summary ? formatValue(summary.total_rainfall_mm, " mm") : "—",
      foot: summary ? summary.location : "Historical total",
      icon: "☀",
      tone: "amber",
    },
  ];

  const pageError = Object.entries(loadErrors)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");

  return (
    <div className="ci-app">
      {menuOpen && (
        <button
          className="ci-backdrop"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside className={`ci-sidebar ${menuOpen ? "ci-sidebar--open" : ""}`}>
        <div className="ci-brand">
          <span className="ci-brand__mark">C</span>
          <span className="ci-brand__text">
            <strong>Climate</strong>
            <span>INTELLIGENCE</span>
          </span>
          <button
            className="ci-close-menu"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            ×
          </button>
        </div>

        <div className="ci-sidebar__label">WORKSPACE</div>
        <nav className="ci-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              key={item.page}
              className={`ci-nav__item ${activePage === item.page ? "is-active" : ""}`}
              onClick={() => navigate(item.page)}
              aria-current={activePage === item.page ? "page" : undefined}
            >
              <span className="ci-nav__icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              {activePage === item.page && <span className="ci-nav__indicator" />}
            </button>
          ))}
        </nav>

        <div className="ci-sidebar__bottom">
          <div className="ci-status">
            <span className={`ci-status__dot ${pageError ? "is-error" : ""}`} />
            <div>
              <strong>Climate data service</strong>
              <span>{pageError ? "One or more endpoints need attention" : "Connected to the backend"}</span>
            </div>
          </div>
          <div className="ci-sidebar__footer">
            <span>CLIMATE INTELLIGENCE</span>
            <span>Research &amp; Analytics</span>
          </div>
        </div>
      </aside>

      <main className="ci-main">
        <header className="ci-topbar">
          <button
            className="ci-menu-button"
            aria-label="Open navigation"
            onClick={() => setMenuOpen(true)}
          >
            ☰
          </button>
          <div className="ci-breadcrumb">
            <span>Workspace</span>
            <span className="ci-breadcrumb__separator">/</span>
            <strong>{activeLabel}</strong>
          </div>
          <div className="ci-topbar__right">
            <span className="ci-live-indicator"><span />Backend data</span>
            <div className="ci-avatar" aria-label="Climate workspace">CI</div>
          </div>
        </header>

        <div className="ci-content">
          <section className="ci-welcome">
            <div>
              <div className="ci-eyebrow">
                <span className="ci-eyebrow__line" />
                CLIMATE MONITORING PLATFORM
              </div>
              <h1>{activeLabel}</h1>
              <p>
                {activePage === "assistant"
                  ? "Ask questions grounded in your indexed climate documents."
                  : "Explore weather observations and model results served by your climate backend."}
              </p>
            </div>
            <button
              className="ci-refresh"
              onClick={() => loadDashboard()}
              disabled={loading}
            >
              <span aria-hidden="true">↻</span>
              {loading ? "Refreshing…" : "Refresh data"}
            </button>
          </section>

          {pageError && (
            <div className="ci-alert" role="status">
              <span>ⓘ</span>
              <div>
                <strong>Some backend data could not be loaded</strong>
                <p>{pageError}</p>
              </div>
            </div>
          )}

          {activePage === "dashboard" && (
            <>
              <section className="ci-section">
                <div className="ci-section-heading">
                  <div>
                    <h2>Weather indicators</h2>
                    <p>Historical data summary from the weather API</p>
                  </div>
                  <span className="ci-section-tag">LIVE API DATA</span>
                </div>
                <div className="ci-metric-grid">
                  {metricCards.map((metric) => (
                    <article className="ci-metric-card" key={metric.label}>
                      <div className="ci-metric-card__top">
                        <span>{metric.label}</span>
                        <span className={`ci-metric-card__icon ${metric.tone}`} aria-hidden="true">
                          {metric.icon}
                        </span>
                      </div>
                      <div className="ci-metric-card__value">
                        {loading && !summary ? "…" : metric.value}
                      </div>
                      <div className="ci-metric-card__foot">
                        <span className="ci-metric-card__dot" />
                        {metric.foot}
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="ci-analysis-grid">
                <article className="ci-panel ci-rainfall-panel">
                  <div className="ci-panel__heading">
                    <div>
                      <h2>Monthly rainfall</h2>
                      <p>Average daily precipitation for each month</p>
                    </div>
                    <span className="ci-panel__symbol">↗</span>
                  </div>
                  <MonthlyRainfall records={rainfall} loading={loading} />
                </article>
                <article className="ci-panel ci-map-panel">
                  <div className="ci-panel__heading">
                    <div>
                      <h2>Climate monitoring</h2>
                      <p>Geographic context for your observations</p>
                    </div>
                    <span className="ci-panel__symbol">◎</span>
                  </div>
                  <ClimateMap />
                </article>
              </section>

              <section className="ci-panel ci-observations">
                <div className="ci-panel__heading">
                  <div>
                    <h2>Recent observations</h2>
                    <p>Latest daily records received from the weather API</p>
                  </div>
                  <span className="ci-section-tag">RECENT DATA</span>
                </div>
                <WeatherTable records={recent} loading={loading} />
              </section>
            </>
          )}

          {activePage === "rainfall" && (
            <section className="ci-panel ci-page-panel">
              <div className="ci-panel__heading">
                <div>
                  <h2>Rainfall by month</h2>
                  <p>Historical monthly averages from <code>/weather/monthly-rainfall</code></p>
                </div>
                <span className="ci-section-tag">MILLIMETRES</span>
              </div>
              <MonthlyRainfall records={rainfall} loading={loading} />
              <div className="ci-subsection-heading">
                <h2>Latest measurements</h2>
                <p>Daily rainfall values from the most recent observations</p>
              </div>
              <WeatherTable records={recent} loading={loading} />
            </section>
          )}

          {activePage === "insights" && (
            <>
              <section className="ci-section">
                <div className="ci-section-heading">
                  <div>
                    <h2>Dataset overview</h2>
                    <p>Coverage and data quality from <code>/weather/summary</code></p>
                  </div>
                  <span className="ci-section-tag">{summary?.location || "WEATHER DATA"}</span>
                </div>
                <div className="ci-metric-grid">
                  {[
                    ["Coverage", summary ? `${summary.start_date} – ${summary.end_date}` : "—"],
                    ["Missing values", summary ? formatValue(summary.missing_values, "", 0) : "—"],
                    ["Rainy-day share", summary ? `${((summary.rainy_days / summary.records) * 100).toFixed(1)}%` : "—"],
                    ["Average rainfall", summary ? formatValue(summary.average_daily_rainfall_mm, " mm", 2) : "—"],
                  ].map(([label, value]) => (
                    <article className="ci-metric-card ci-insight-card" key={label}>
                      <div className="ci-metric-card__top">{label}</div>
                      <div className="ci-insight-value">{loading && !summary ? "…" : value}</div>
                    </article>
                  ))}
                </div>
              </section>
              <section className="ci-panel ci-observations">
                <div className="ci-panel__heading">
                  <div>
                    <h2>Recent weather conditions</h2>
                    <p>Temperature, rainfall, humidity, and wind from the daily dataset</p>
                  </div>
                </div>
                <WeatherTable records={recent} loading={loading} />
              </section>
            </>
          )}

          {activePage === "forecast" && (
            <section className="ci-panel ci-forecast-panel">
              <div className="ci-panel__heading">
                <div>
                  <h2>Saved rainfall forecast</h2>
                  <p>Model output from the backend at <code>/forecast/latest</code></p>
                </div>
                <span className="ci-section-tag">RANDOM FOREST</span>
              </div>
              {loading && !forecast ? (
                <div className="ci-empty-state">Loading forecast…</div>
              ) : forecast ? (
                <>
                  <div className="ci-forecast-value">
                    {formatValue(forecast.predicted_rainfall_mm, " mm", 2)}
                  </div>
                  <p className="ci-forecast-date">
                    Predicted rainfall for {forecast.forecast_date}
                  </p>
                  <div className="ci-forecast-note">{forecast.note}</div>
                </>
              ) : (
                <div className="ci-empty-state">
                  <strong>Forecast unavailable</strong>
                  <p>{loadErrors.forecast || "The backend did not return a forecast."}</p>
                  <p>Run <code>python train_model.py</code> to generate the saved forecast.</p>
                </div>
              )}
            </section>
          )}

          {activePage === "assistant" && (
            <section className="ci-panel ci-assistant-panel">
              <div className="ci-panel__heading">
                <div>
                  <h2>AI Climate Assistant</h2>
                  <p>Answers are based on indexed climate PDFs and include source references.</p>
                </div>
                <span className="ci-panel__symbol">✳</span>
              </div>

              <div className="ci-index-box">
                <div>
                  <strong>Climate document library</strong>
                  <p>Index PDFs placed in the project’s <code>documents/</code> folder before asking questions.</p>
                </div>
                <button className="ci-refresh" onClick={indexDocuments} disabled={indexing}>
                  {indexing ? "Indexing…" : "Index documents"}
                </button>
              </div>
              {indexError && <p className="ci-inline-error" role="alert">{indexError}</p>}
              {indexResult && (
                <div className="ci-index-result" role="status">
                  <strong>{indexResult.message}</strong>
                  {indexResult.new_chunks_indexed !== undefined && (
                    <span>{indexResult.new_chunks_indexed} new chunks indexed · {indexResult.total_chunks_in_database} total</span>
                  )}
                  {indexResult.failed_files?.length > 0 && (
                    <ul>
                      {indexResult.failed_files.map((file) => (
                        <li key={file.file}>{file.file}: {file.error}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <div className="ci-chat-messages" aria-live="polite">
                {chatMessages.length === 0 && (
                  <div className="ci-chat-welcome">
                    <span aria-hidden="true">✳</span>
                    <strong>What would you like to know?</strong>
                    <p>Ask a question about the climate documents indexed in this workspace.</p>
                  </div>
                )}
                {chatMessages.map((message, index) => (
                  <article className={`ci-chat-message ci-chat-message--${message.role}`} key={`${message.role}-${index}`}>
                    <strong>{message.role === "user" ? "You" : "Climate assistant"}</strong>
                    <p>{message.content}</p>
                    {message.sources?.length > 0 && (
                      <div className="ci-chat-sources">
                        <strong>Sources</strong>
                        {message.sources.map((source) => (
                          <span key={`${source.source}-${source.page}`}>
                            {source.source}, page {source.page}
                          </span>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
                {chatLoading && <div className="ci-chat-pending">Searching the climate documents…</div>}
              </div>
              {chatError && <p className="ci-inline-error" role="alert">{chatError}</p>}
              <form className="ci-chat-form" onSubmit={submitQuestion}>
                <label className="ci-sr-only" htmlFor="climate-question">Your climate question</label>
                <textarea
                  id="climate-question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask a question about your climate documents…"
                  rows={2}
                  maxLength={2000}
                  disabled={chatLoading}
                />
                <button className="ci-chat-submit" type="submit" disabled={chatLoading || !question.trim()}>
                  {chatLoading ? "Sending…" : "Ask"}
                </button>
              </form>
            </section>
          )}

          <footer className="ci-footer">
            <span>Climate Intelligence</span>
            <span>Weather data &amp; climate research</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
