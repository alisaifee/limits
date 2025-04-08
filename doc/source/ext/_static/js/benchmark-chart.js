import { render, html } from "https://unpkg.com/uhtml@3.2.1?module";
import { fetchBenchmarkData } from "./benchmark-loader.js";
const KNOWN_PARAMS = ["storage_type", "limit", "strategy", "async"];

function getBenchmarkData(result, query) {
  let benchmarks = result.benchmarks;
  return benchmarks.filter(function (benchmark) {
    let okay = true;
    if (query) {
      Object.entries(query).forEach((entry) => {
        if (entry[0] != "group" && benchmark.params[entry[0]] != entry[1]) {
          okay = false;
        }
        if (entry[0] == "group" && entry[1] != benchmark.group) {
          okay = false;
        }
      });
    }
    return okay;
  });
}

function formatRateLimit(str) {
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
    let value = param[1];
    if (param[0] === "limit") {
      value = formatRateLimit(value);
    }
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
    if (!queryParam.includes(param[0]) && KNOWN_PARAMS.includes(param[0])) {
      additional[param[0]] = param[1];
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
    let source = chart.dataset.source;
    let filters = JSON.parse(chart.dataset.filters);
    let query = JSON.parse(chart.dataset.query);
    let sortBy = JSON.parse(
      chart.dataset.sortBy || '["storage_type", "limit"]',
    );
    if (!dispatched.has(source)) {
      fetchBenchmarkData(`${source}.json`)
        .then((result) => {
          window.Benchmarks[source] = result;
          let event = new Event(`${source}-loaded`);
          console.log("Happiness");
          window.dispatchEvent(event);
        })
        .catch((error) => {
          let event = new Event(`${source}-failed`);
          console.log("Sadness");
          window.dispatchEvent(event);
        });
    }
    dispatched.add(source);
    window.addEventListener(`${chart.dataset.source}-failed`, function () {
      render(
        chart,
        html`
          <div class="benchmark-chart-error">Benchmark data not available.</div>
        `,
      );
    });
    window.addEventListener(`${chart.dataset.source}-loaded`, function () {
      let results = Benchmarks[chart.dataset.source];
      let unsorted = getBenchmarkData(results, query);
      let data = sortBenchmarksByParams(
        getBenchmarkData(results, query),
        sortBy,
      );

      const layout = {
        yaxis: {
          title: { text: "Time (ms)" },
          exponentformat: "none",
          ticksuffix: " ms",
          tickformat: ",.2f",
        },
      };
      Plotly.newPlot(
        chart,
        data.map(function (benchmark) {
          let item = {
            type: "box",
            name: nameTransform(benchmark, true, query),
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
            legendgroup: benchmark.params.storage_type,
            legendgrouptitle: { text: benchmark.params.storage_type },
          };
          return item;
        }),
        layout,
      );
    });
  });
});
