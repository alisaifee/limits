import { render, html } from "https://unpkg.com/uhtml@3.2.1?module";
document.addEventListener("DOMContentLoaded", function () {
  const details = document.querySelectorAll(".benchmark-details");
  details.forEach((detail) => {
    let source = detail.dataset.source;
    if (!dispatched.has(source)) {
      fetchBenchmarkData(`${source}.json`).then((result) => {
        window.Benchmarks[source] = result;
        event = new Event(`${source}-loaded`);
        window.dispatchEvent(event);
      });
    }
    dispatched.add(source);
    window.addEventListener(`${detail.dataset.source}-loaded`, function () {
      const machine_info = window.Benchmarks[source].machine_info;
      const commit_info = window.Benchmarks[source].commit_info;
      const cpu = window.Benchmarks[source].machine_info.cpu;
      console.log(machine_info);
      render(
        detail,
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
    });
  });
});
