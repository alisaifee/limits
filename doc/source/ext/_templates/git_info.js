window.GITBRANCH = "{{branch | replace('.', '-')}}";
window.GITSHA = "{{sha}}";

function getReleases() {
  return fetch("https://pypi.org/pypi/limits/json")
    .then((res) => {
      if (!res.ok) throw new Error("Releases not found");
      return res.json();
    })
    .catch((error) => [error]);
}

getReleases().then((response) => {
  const releases = Object.entries(response.releases).map((entry) => entry[0]);
  window.LATEST_RELEASES = releases.slice(-5).reverse();
});
