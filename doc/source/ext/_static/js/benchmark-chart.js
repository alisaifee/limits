import { render, html } from "https://unpkg.com/uhtml@3.2.1?module";
import { BenchmarkLoader } from "./benchmark-loader.js";
const KNOWN_PARAMS = [
  "storage_type",
  "limit",
  "strategy",
  "async",
  "percentage_full",
];
let dispatched = new Set();
window.Benchmarks = {};
let currentLoader = new BenchmarkLoader();
let compareLoaders = {};

class BenchmarkChartUtils {
  static getBenchmarkData(result, query) {
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

  static formatParam(key, str) {
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

  static nameTransform(benchmark, stripParams, query) {
    let name = benchmark.name;
    let params = benchmark.params;
    name = name
      .replace(/\[.*?\]/, "")
      .replace("_async", "")
      .replaceAll("_", "-");
    name = name.replace(benchmark.group, "");
    let queryParam = Object.entries(query).map((entry) => entry[0]);
    let additional = BenchmarkChartUtils.getRemainingGroups(benchmark, query);
    Object.entries(additional).forEach((param) => {
      let value = BenchmarkChartUtils.formatParam(param[0], param[1]);
      if (name) {
        name += ` - ${value}`;
      } else {
        name = `${value}`;
      }
    });
    return name;
  }

  static getRemainingGroups(benchmark, query) {
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

  static getColorForStorage(storageType) {
    const storageColorMap = {
      memory: window
        .getComputedStyle(document.body)
        .getPropertyValue("--color-purple"),
      mongodb: window
        .getComputedStyle(document.body)
        .getPropertyValue("--color-yellow"),
      memcached: window
        .getComputedStyle(document.body)
        .getPropertyValue("--color-blue"),
      redis: window
        .getComputedStyle(document.body)
        .getPropertyValue("--color-red"),
    };

    // Fallback color if an unknown storageType appears
    return storageColorMap[storageType] || "#7f7f7f"; // gray
  }

  static sortBenchmarksByParams(benchmarks, sortKeys) {
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

  static fetchComparisonData(source, comparisonSource) {
    if (!compareLoaders[comparisonSource]) {
      compareLoaders[comparisonSource] = new BenchmarkLoader([
        `https://${comparisonSource.replaceAll(".", "-")}--py-limits.netlify.app/`,
      ]);
    }
    return compareLoaders[comparisonSource].fetchBenchmarkData(source);
  }
}

class BenchmarkChart {
  constructor(node) {
    this.chart = node;
    this.source = this.chart.dataset.source;
    this.filters = JSON.parse(this.chart.dataset.filters);
    this.query = JSON.parse(this.chart.dataset.query);
    this.paramMapping = JSON.parse(this.chart.dataset.paramMapping);
    this.chartId = this.chart.dataset.chartId;
    this.currentCompare = null;
    this.sortBy = JSON.parse(
      this.chart.dataset.sortBy || '["storage_type", "limit"]',
    );
    let self = this;
    render(
      this.chart,
      html`
        <div class="benchmark-chart-loading">
          <span>Loading</span>
        </div>
      `,
    );
    if (!dispatched.has(this.source)) {
      currentLoader
        .fetchBenchmarkData(this.source)
        .then((result) => {
          let event = new Event(`${self.source}-loaded`);
          window.dispatchEvent(event);
        })
        .catch((error) => {
          let event = new Event(`${self.source}-failed`);
          window.dispatchEvent(event);
        });
    }
    dispatched.add(this.source);
    window.addEventListener(`${this.source}-failed`, function () {
      self.handleError();
    });
    window.addEventListener(`${this.source}-loaded`, function () {
      self.render();
    });
  }
  handleError() {
    this.chart.querySelector(".benchmark-chart-loading")?.remove();
    render(
      this.chart,
      html`
        <div class="benchmark-chart-error">Benchmark data not available.</div>
      `,
    );
  }
  renderCompare() {
    const compareTargets = ["master", "stable", "4.x"]
      .concat(window.LATEST_RELEASES || [])
      .filter((element) => element != window.GITBRANCH);
    let self = this;
    const compareDropdown = html`
      <div class="compare" title="Compare against another release or branch">
        <label for="compare-select">
          Compare with
          <select
            onchange=${(e) => {
              const value = e.target.value;
              self.currentCompare = value;
              if (value !== "") {
                BenchmarkChartUtils.fetchComparisonData(
                  self.source,
                  value,
                ).then(function (comparisonData) {
                  self.currentComparisonData = comparisonData;
                  self.renderChartWithFilters();
                });
              } else {
                self.currentComparisonData = null;
                self.renderChartWithFilters();
              }
            }}
          >
            <option value=""></option>
            ${compareTargets.map(
              (val) => html`
                <option
                  value=${val}
                  ?selected=${this.currentCompare == val.toString()}
                >
                  ${val}
                </option>
              `,
            )}
          </select>
        </label>
      </div>
    `;
    render(
      this.compareTarget,
      html`<div class="compare-dropdowns">${compareDropdown}</div>`,
    );
  }
  renderDropdowns() {
    const dropdowns = Object.entries(this.filters).map(([key]) => {
      const fullName = `${this.chartId}-${key}`;
      const uniqueValues = [
        ...new Set(this.allBenchmarks.map((b) => b.params?.[key])),
      ].sort();
      const isBoolean =
        uniqueValues.length === 2 &&
        uniqueValues.includes(true) &&
        uniqueValues.includes(false);
      let self = this;
      if (isBoolean) {
        return html`
          <div class="benchmark-filter" title=${this.paramMapping[key]?.info}>
            <input
              type="checkbox"
              id=${fullName}
              ?checked=${self.currentFilters[key] === true}
              onchange=${(e) => {
                self.currentFilters[key] = e.target.checked;
                self.renderChartWithFilters();
              }}
            />
            <label for=${fullName}>
              ${self.paramMapping[key]?.display || key}
            </label>
          </div>
        `;
      } else {
        return html`
          <div class="benchmark-filter" title=${self.paramMapping[key]?.info}>
            <label for=${fullName}>
              ${self.paramMapping[key]?.display || key}
              <select
                id=${fullName}
                onchange=${(e) => {
                  const value = e.target.value;
                  if (value) {
                    self.currentFilters[key] =
                      value === "false"
                        ? false
                        : value === "true"
                          ? true
                          : value;
                  } else {
                    self.currentFilters[key] = "";
                  }
                  self.renderChartWithFilters();
                }}
              >
                <option value="" ?selected=${self.currentFilters[key] == ""}>
                  All
                </option>
                ${uniqueValues.map(
                  (val) => html`
                    <option
                      value=${val}
                      ?selected=${self.currentFilters[key] == val.toString()}
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
      this.dropdownTarget,
      html`<div class="benchmark-filter-dropdowns">${dropdowns}</div>`,
    );
  }
  renderChartWithFilters() {
    const queryFilter = { ...this.query, ...this.currentFilters };
    let data = BenchmarkChartUtils.sortBenchmarksByParams(
      BenchmarkChartUtils.getBenchmarkData(this.results, queryFilter),
      this.sortBy,
    );
    let comparisonData = [];
    let comparing = false;
    if (this.currentComparisonData?.benchmarks) {
      comparisonData = BenchmarkChartUtils.sortBenchmarksByParams(
        BenchmarkChartUtils.getBenchmarkData(
          this.currentComparisonData,
          queryFilter,
        ),
        this.sortBy,
      );
      comparisonData.forEach((benchmark) => {
        benchmark.forComparison = true;
      });
      comparing = true;
      data = data.concat(comparisonData);
    }
    let legendGroupKey =
      queryFilter?.storage_type == ""
        ? "storage_type"
        : Object.entries(queryFilter).find((entry) => entry[1] === "")?.[0];
    function legendKeyFunc(benchmark, key) {
      return key === "group" ? benchmark.group : benchmark.params[key];
    }

    Plotly.newPlot(
      this.chartTarget,
      data.map((benchmark) => ({
        type: "box",
        name: BenchmarkChartUtils.nameTransform(benchmark, true, queryFilter),
        opacity: benchmark.forComparison ? 0.75 : comparing ? 0.5 : 1,
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
          color: benchmark.forComparison
            ? "#39FF14"
            : BenchmarkChartUtils.getColorForStorage(
                benchmark.params.storage_type,
              ),
        },
        showlegend: !benchmark.forComparison,
        legendgroup: legendKeyFunc(benchmark, legendGroupKey),
        legendgrouptitle: {
          text: BenchmarkChartUtils.formatParam(
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
        xaxis: { automargin: true },
        title: comparing
          ? {
              text: `Comparing against: ${this.currentCompare}`,
              font: { color: "39FF14" },
            }
          : {},
      },
      {
        responsive: true,
        displaylogo: false,
      },
    );
  }
  render() {
    this.chart.innerHTML = "";
    this.chart.querySelector(".benchmark-chart-loading")?.remove();
    this.results = currentLoader.sources[this.source];
    this.allBenchmarks = BenchmarkChartUtils.getBenchmarkData(
      this.results,
      this.query,
    );
    this.currentFilters = Object.fromEntries(
      Object.entries(this.filters).map(([key, value]) => {
        return typeof value.default === "boolean"
          ? [key, value.default]
          : [key, value.default != null ? value.default.toString() : ""];
      }),
    );
    this.currentCompare = "";
    this.currentComparisonData = null;
    this.dropdownTarget = document.createElement("div");
    this.compareTarget = document.createElement("div");
    this.dropdownTarget.classList.add("benchmark-filters");
    this.chartTarget = document.createElement("div");
    this.chart.append(this.chartTarget);
    this.chart.append(this.dropdownTarget);
    this.chart.append(this.compareTarget);
    this.renderDropdowns();
    this.renderCompare();
    this.renderChartWithFilters();
    let initial = true;
    this.chartTarget.on("plotly_afterplot", function () {
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
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const charts = document.querySelectorAll(".benchmark-chart");
  charts.forEach((chart) => {
    const chartObject = new BenchmarkChart(chart);
  });
});
