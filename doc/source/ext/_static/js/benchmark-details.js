import { render, html } from "https://unpkg.com/uhtml@3.2.1?module";
import { BenchmarkLoader } from "./benchmark-loader.js";

let currentLoader = new BenchmarkLoader();
let dispatched = new Set();

class BenchmarkDetails {
  constructor(node) {
    this.detail = node;
    this.source = this.detail.dataset.source;
    let self = this;
    if (!dispatched.has(this.source)) {
      currentLoader
        .fetchBenchmarkData(self.source)
        .then((result) => {
          let event = new Event(`${self.source}-details-loaded`);
          window.dispatchEvent(event);
        })
        .catch((error) => {
          let event = new Event(`${self.source}-details-failed`);
          window.dispatchEvent(event);
        });
    }
    dispatched.add(this.source);
    window.addEventListener(`${this.source}-details-failed`, function () {
      self.handleError();
    });
    window.addEventListener(`${this.source}-details-loaded`, function () {
      self.render();
    });
  }
  handleError() {
    render(
      this.detail,
      html`
        <div class="benchmark-details-error">Benchmark data not available.</div>
      `,
    );
  }
  render() {
    const machine_info = currentLoader.sources[this.source].machine_info;
    const commit_info = currentLoader.sources[this.source].commit_info;
    const cpu = currentLoader.sources[this.source].machine_info.cpu;
    render(
      this.detail,
      html`
        <table class="benchmark-details-section">
          <thead>
            <tr>
              <th>Machine Information</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Operating System</td>
              <td>${machine_info.system} (${machine_info.release})</td>
            </tr>
            <tr>
              <td>CPU</td>
              <td>
                ${cpu.brand_raw} ${cpu.processor} @ ${cpu.hz_actual_friendly}
              </td>
            </tr>
            <tr>
              <td>Python</td>
              <td>${machine_info.python_version}</td>
            </tr>
          </tbody>
        </table>
        <table class="benchmark-details-section">
          <thead>
            <tr>
              <th>Source Information</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Branch</td>
              <td>${commit_info.branch}</td>
            </tr>
            <tr>
              <td>Commit Hash</td>
              <td>${commit_info.id}</td>
            </tr>
          </tbody>
        </table>
        <table class="benchmark-details-section">
          <thead>
            <tr>
              <th>Storage Information</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Redis</td>
              <td>${machine_info.redis.redis_version}</td>
            </tr>
            <tr>
              <td>Memcached</td>
              <td>${machine_info.memcached.version}</td>
            </tr>
            <tr>
              <td>MongoDB</td>
              <td>${machine_info.mongodb.version}</td>
            </tr>
          </tbody>
        </table>
      `,
    );
  }
}
document.addEventListener("DOMContentLoaded", function () {
  const details = document.querySelectorAll(".benchmark-details");
  details.forEach((detail) => {
    new BenchmarkDetails(detail);
  });
});
