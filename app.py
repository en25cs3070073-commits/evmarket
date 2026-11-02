import json
import os
from urllib.parse import parse_qsl, urlencode

from flask import Flask, abort, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Forces a published view to render standalone inside an iframe rather than
# opening the full Tableau authoring chrome.
EMBED_PARAMS = {
    ":language": "en-US",
    ":embed": "true",
    ":toolbar": "auto",
    ":display_count": "n",
}


def load_config():
    with open(os.path.join(BASE_DIR, "tableau_urls.json"), encoding="utf-8") as fh:
        return json.load(fh)


def build_embed_src(url):
    if not url:
        return ""
    base, _, query = url.partition("?")
    merged = dict(parse_qsl(query, keep_blank_values=True))
    merged.update(EMBED_PARAMS)
    return base + "?" + urlencode(merged)


CONFIG = load_config()
PAGES = {page["key"]: page for page in CONFIG["pages"]}

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html", config=CONFIG, pages=CONFIG["pages"])


@app.route("/<key>")
def page(key):
    target = PAGES.get(key)
    if target is None:
        abort(404)
    return render_template(
        "page.html",
        page=target,
        config=CONFIG,
        embed_src=build_embed_src(target["url"]),
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", config=CONFIG), 404


if __name__ == "__main__":
    app.run(debug=True)
