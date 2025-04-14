const BENCHMARK_PATHS = [
  `https://${GITSHA}--py-limits.netlify.app`,
  `https://${GITBRANCH}--py-limits.netlify.app`,
];

class BenchmarkLoader {
  constructor(paths) {
    this.paths = paths || BENCHMARK_PATHS;
    this.sources = {};
  }
  fetchBenchmarkData(source) {
    if (this.sources[source] != null) {
      return Promise.resolve(this.sources[source]);
    }
    let attempts = 0;
    let self = this;
    function tryFetch() {
      if (attempts >= self.paths.length) {
        return Promise.reject(new Error("All fetch attempts failed."));
      }
      const base = self.paths[attempts++];
      const url = `${base}/${source}.json`;
      return fetch(url, { method: "HEAD" })
        .then((headRes) => {
          if (!headRes.ok) throw new Error("HEAD check failed");
          return fetch(url).then((res) => {
            if (!res.ok) throw new Error(`GET failed from ${url}`);
            return res.json().then((json) => {
              self.sources[source] = json;
              return Promise.resolve(self.sources[source]);
            });
          });
        })
        .catch((err) => {
          return tryFetch();
        });
    }

    return tryFetch();
  }
}

export { BenchmarkLoader };
