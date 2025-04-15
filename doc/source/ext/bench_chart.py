from __future__ import annotations

import json
import os
import uuid
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import ensuredir

if TYPE_CHECKING:
    from sphinx.application import Sphinx

here = os.path.dirname(os.path.abspath(__file__))


def check_bool(value):
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"
    return value


def query(argument):
    if not argument.strip():
        return {}
    queries = {}
    for query in argument.strip().split(","):
        key, value = query.split("=")
        queries[key] = check_bool(value)
    return queries


def filters(argument):
    filters: dict[str, dict[str, str | bool]] = {}
    for filter in argument.strip().split(","):
        source, default = filter.split("=")
        if ":" in source:
            source, label = source.split(":")
        else:
            source, label = source, source
        filters[source] = {"label": label, "default": check_bool(default)}
    return filters


def sortBy(argument):
    return [k.strip() for k in argument.split(",")] if argument else []


class BenchmarkDetails(SphinxDirective):
    required_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "source": str,
    }
    has_content = False

    def run(self):
        source = self.options.get("source", "benchmark-summary")
        html = f"""
                <div
                    class='benchmark-details'
                    data-source='{source}'
                </div>
                """

        return [nodes.raw("", html, format="html")]


class BenchmarkChart(SphinxDirective):
    final_argument_whitespace = False
    option_spec = {
        "title": str,
        "source": str,
        "query": query,
        "filters": filters,
        "sort": sortBy,
    }
    has_content = False

    def run(self):
        title = self.options.get("title", "")
        source = self.options.get("source", "benchmark-summary")
        filters = self.options.get("filters", {})
        query = self.options.get("query", {})
        sortBy = self.options.get("sort", [])
        html = f"""
                <div
                    class='benchmark-chart'
                    data-title='{title}'
                    data-source='{source}'
                    data-filters='{json.dumps(filters)}'
                    data-query='{json.dumps(query)}'
                    data-sort-by='{json.dumps(sortBy)}'
                    data-chart-id='{uuid.uuid4().hex}'
                    data-param-mapping='{json.dumps(self.env.config.benchmark_param_mapping)}'>
                </div>
                """

        return [nodes.raw("", html, format="html")]


def render_js_template(app) -> None:
    context = {
        "branch": app.config.benchmark_git_context.get("branch", ""),
        "sha": app.config.benchmark_git_context.get("sha", ""),
    }

    template = app.builder.templates.environment.get_template("git_info.js")
    rendered_js = template.render(context)

    out_dir = os.path.join(app.outdir, "_static", "js")
    ensuredir(out_dir)
    out_path = os.path.join(out_dir, "git_info.js")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered_js)
    app.add_js_file("js/git_info.js")


def setup(app: Sphinx):
    app.add_directive("benchmark-chart", BenchmarkChart)
    app.add_directive("benchmark-details", BenchmarkDetails)
    app.add_config_value("benchmark_git_context", default={}, rebuild="env")
    app.add_config_value("benchmark_param_mapping", default={}, rebuild="env")

    def add_assets(app, env) -> None:
        static_path = os.path.join(here, "_static")
        if static_path not in app.config.html_static_path:
            app.config.html_static_path.append(static_path)
        app.add_js_file("js/benchmark-chart.js", type="module")
        app.add_js_file("js/benchmark-details.js", type="module")
        app.add_js_file("js/benchmark-loader.js", type="module")
        app.add_js_file("https://cdn.plot.ly/plotly-3.0.1.min.js")
        app.add_css_file("benchmark-chart.css")

    app.config.templates_path += [os.path.join(here, "_templates")]
    app.connect("env-updated", add_assets)
    app.connect("builder-inited", render_js_template)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
