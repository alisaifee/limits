const BENCHMARK_PATHS = [
  `https://${GITSHA}--py-limits.netlify.app/`,
  `https://${GITBRANCH}--py-limits.netlify.app/`,
];

window.Benchmarks = new Map();

function fetchBenchmarkData(filename) {
  let attempts = 0;

  function tryFetch() {
    if (attempts >= BENCHMARK_PATHS.length) {
      return Promise.reject("All fetch attempts failed.");
    }

    const base = BENCHMARK_PATHS[attempts++];
    const url = base + filename;

    // First send a HEAD request to quietly check existence
    return fetch(url, { method: "HEAD" })
      .then((headRes) => {
        if (!headRes.ok) throw new Error("HEAD check failed");
        return fetch(url).then((res) => {
          if (!res.ok) throw new Error(`GET failed from ${url}`);
          return res.json();
        });
      })
      .catch(() => tryFetch());
  }

  return tryFetch();
}
