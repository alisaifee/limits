import { render, html } from "https://unpkg.com/uhtml@3.2.1?module";
import { fetchBenchmarkData } from "./benchmark-loader.js";
const KNOWN_PARAMS = [
  "storage_type",
  "limit",
  "strategy",
  "async",
  "percentage_full",
];

function getBenchmarkData(result, query) {
  let benchmarks = result.benchmarks;
  return benchmarks.filter(function (benchmark) {
    let okay = true;
    if (query) {
      Object.entries(query).forEach((entry) => {
        let key = entry[0];
        let value = entry[1];
        if (
          key != "group" &&
          !(value === "") && // i.e. any.
          benchmark.params[key] != null &&
          benchmark.params[key] != value
        ) {
          okay = false;
        } else if (key == "group" && value != benchmark.group) {
          okay = false;
        }
      });
    }
    return okay;
  });
}

function formatParam(key, str) {
  if (key === "limit") {
    var m = str.match(/(\d+(?:\.\d+)?)\s+per\s+1\s+(\w+)/i);
    if (!m) return str;
    var n = parseFloat(m[1]),
      u = m[2].toLowerCase(),
      num =
        n >= 1000
          ? (n / 1000) % 1 === 0
            ? n / 1000 + "K"
            : (n / 1000).toFixed(1) + "K"
          : n.toString(),
      umap = {
        second: "s",
        seconds: "s",
        minute: "min",
        minutes: "mins",
        hour: "hr",
        hours: "hr",
        day: "day",
        days: "day",
      };
    return num + "/" + (umap[u] || u);
  } else if (key === "percentage_full") {
    return `${str}% Seeded`;
  }
  return str;
}

function nameTransform(benchmark, stripParams, query) {
  let name = benchmark.name;
  let params = benchmark.params;
  name = name
    .replace(/\[.*?\]/, "")
    .replace("_async", "")
    .replaceAll("_", "-");
  name = name.replace(benchmark.group, "");
  let queryParam = Object.entries(query).map((entry) => entry[0]);
  let additional = getRemainingGroups(benchmark, query);
  Object.entries(additional).forEach((param) => {
    let value = formatParam(param[0], param[1]);
    if (name) {
      name += ` - ${value}`;
    } else {
      name = `${value}`;
    }
  });
  return name;
}

function getRemainingGroups(benchmark, query) {
  let queryParam = Object.entries(query).map((entry) => entry[0]);
  let additional = {};
  Object.entries(benchmark.params).forEach((param) => {
    const key = param[0];
    const value = param[1];
    if (
      (!queryParam.includes(key) || query?.[key] === "") &&
      KNOWN_PARAMS.includes(key)
    ) {
      additional[key] = value;
    }
  });
  return additional;
}

function getColorForStorage(storageType) {
  const storageColorMap = {
    memory: window
      .getComputedStyle(document.body)
      .getPropertyValue("--color-purple"),
    mongodb: window
      .getComputedStyle(document.body)
      .getPropertyValue("--color-yellow"),
    memcached: window
      .getComputedStyle(document.body)
      .getPropertyValue("--color-aqua"),
    redis: window
      .getComputedStyle(document.body)
      .getPropertyValue("--color-red"),
  };

  // Fallback color if an unknown storageType appears
  return storageColorMap[storageType] || "#7f7f7f"; // gray
}

function sortBenchmarksByParams(benchmarks, sortKeys) {
  return benchmarks.sort(function (a, b) {
    for (const key of sortKeys) {
      let valA = (a.params?.[key] || "").toLowerCase();
      let valB = (b.params?.[key] || "").toLowerCase();
      if (key === "limit") {
        valA = parseInt(valA.split(" ")[0], 10);
        valB = parseInt(valB.split(" ")[0], 10);
      }
      if (valA < valB) return -1;
      if (valA > valB) return 1;
    }
    return a.name.localeCompare(b.name);
  });
}

let dispatched = new Set();

document.addEventListener("DOMContentLoaded", function () {
  const charts = document.querySelectorAll(".benchmark-chart");
  charts.forEach((chart) => {
    const source = chart.dataset.source;
    const filters = JSON.parse(chart.dataset.filters);
    const query = JSON.parse(chart.dataset.query);
    const paramMapping = JSON.parse(chart.dataset.paramMapping);
    const chartId = chart.dataset.chartId;
    let sortBy = JSON.parse(
      chart.dataset.sortBy || '["storage_type", "limit"]',
    );
    render(
      chart,
      html`
        <div class="benchmark-chart-loading">
          <span>Loading</span>
        </div>
      `,
    );
    if (!dispatched.has(source)) {
      fetchBenchmarkData(`${source}.json`)
        .then((result) => {
          window.Benchmarks[source] = result;
          let event = new Event(`${source}-loaded`);
          window.dispatchEvent(event);
        })
        .catch((error) => {
          let event = new Event(`${source}-failed`);
          window.dispatchEvent(event);
        });
    }
    dispatched.add(source);
    window.addEventListener(`${chart.dataset.source}-failed`, function () {
      chart.querySelector(".benchmark-chart-loading")?.remove();
      render(
        chart,
        html`
          <div class="benchmark-chart-error">Benchmark data not available.</div>
        `,
      );
    });
    window.addEventListener(`${chart.dataset.source}-loaded`, function () {
      chart.innerHTML = "";
      chart.querySelector(".benchmark-chart-loading")?.remove();
      const results = Benchmarks[chart.dataset.source];
      const allBenchmarks = getBenchmarkData(results, query);
      const currentFilters = Object.fromEntries(
        Object.entries(filters).map(([key, value]) => {
          return typeof value.default === "boolean"
            ? [key, value.default]
            : [key, value.default != null ? value.default.toString() : ""];
        }),
      );
      const queryFilter = { ...query, ...currentFilters };
      const dropdownTarget = document.createElement("div");
      dropdownTarget.classList.add("benchmark-filters");
      const chartTarget = document.createElement("div");
      chart.append(chartTarget);
      chart.append(dropdownTarget);
      function renderDropdowns() {
        const dropdowns = Object.entries(filters).map(([key]) => {
          const fullName = `${chartId}-${key}`;
          const uniqueValues = [
            ...new Set(allBenchmarks.map((b) => b.params?.[key])),
          ].sort();
          const isBoolean =
            uniqueValues.length === 2 &&
            uniqueValues.includes(true) &&
            uniqueValues.includes(false);
          if (isBoolean) {
            return html`
              <div class="benchmark-filter" title=${paramMapping[key]?.info}>
                <input
                  type="checkbox"
                  id=${fullName}
                  ?checked=${currentFilters[key] === true}
                  onchange=${(e) => {
                    currentFilters[key] = e.target.checked;
                    renderChartWithFilters(currentFilters);
                  }}
                />
                <label for=${fullName}>
                  ${paramMapping[key]?.display || key}
                </label>
              </div>
            `;
          } else {
            return html`
              <div class="benchmark-filter" title=${paramMapping[key]?.info}>
                <label for=${fullName}>
                  ${paramMapping[key]?.display || key}
                  <select
                    id=${fullName}
                    onchange=${(e) => {
                      const value = e.target.value;
                      if (value) {
                        currentFilters[key] =
                          value === "false"
                            ? false
                            : value === "true"
                              ? true
                              : value;
                      } else {
                        currentFilters[key] = "";
                      }
                      renderChartWithFilters(currentFilters);
                    }}
                  >
                    <option value="" ?selected=${currentFilters[key] == ""}>
                      All
                    </option>
                    ${uniqueValues.map(
                      (val) => html`
                        <option
                          value=${val}
                          ?selected=${currentFilters[key] == val.toString()}
                        >
                          ${val}
                        </option>
                      `,
                    )}
                  </select>
                </label>
              </div>
            `;
          }
        });
        render(
          dropdownTarget,
          html`<div class="benchmark-filter-dropdowns">${dropdowns}</div>`,
        );
      }
      function legendKeyFunc(benchmark, key) {
        return key === "group" ? benchmark.group : benchmark.params[key];
      }
      function renderChartWithFilters(currentFilters) {
        const queryFilter = { ...query, ...currentFilters };
        const data = sortBenchmarksByParams(
          getBenchmarkData(results, queryFilter),
          sortBy,
        );
        let legendGroupKey = Object.entries(queryFilter).find(
          (entry) => entry[1] === "",
        )?.[0];
        Plotly.newPlot(
          chartTarget,
          data.map((benchmark) => ({
            type: "box",
            name: nameTransform(benchmark, true, queryFilter),
            y: benchmark.stats.data || [
              benchmark.stats.min * 1e3,
              benchmark.stats.q1 * 1e3,
              benchmark.stats.median * 1e3,
              benchmark.stats.q3 * 1e3,
              benchmark.stats.max * 1e3,
            ],
            boxmean: true,
            boxpoints: false,
            line: { width: 1 },
            marker: {
              color: getColorForStorage(benchmark.params.storage_type),
            },
            showlegend: true,
            legendgroup: legendKeyFunc(benchmark, legendGroupKey),
            legendgrouptitle: {
              text: formatParam(
                legendGroupKey,
                legendKeyFunc(benchmark, legendGroupKey),
              ),
            },
          })),
          {
            yaxis: {
              title: { text: "Time (ms)" },
              exponentformat: "none",
              ticksuffix: " ms",
              tickformat: ",.2f",
            },
          },
          {
            responsive: true,
            displaylogo: false,
          },
        );
      }

      renderDropdowns();
      renderChartWithFilters(currentFilters);
      let initial = true;
      chartTarget.on("plotly_afterplot", function () {
        const { hash } = window.location;
        if (hash && initial) {
          initial = false;
          const target = document.querySelector(hash);
          if (target) {
            setTimeout(function () {
              target.scrollIntoView({ behavior: "instant" });
            }, 10);
          }
        }
      });
    });
  });
});
