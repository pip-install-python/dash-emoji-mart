from __future__ import print_function as _

import json
import os as _os
import sys as _sys

import dash as _dash

# noinspection PyUnresolvedReferences
from ._imports_ import *  # noqa: F401,F403
from ._imports_ import __all__

if not hasattr(_dash, "__plotly_dash") and not hasattr(_dash, "development"):
    print(
        "Dash was not successfully imported. "
        "Make sure you don't have a file "
        'named \n"dash.py" in your current directory.',
        file=_sys.stderr,
    )
    _sys.exit(1)

_basepath = _os.path.dirname(__file__)
_filepath = _os.path.abspath(_os.path.join(_basepath, "package-info.json"))
with open(_filepath) as f:
    package = json.load(f)

package_name = package["name"].replace(" ", "_").replace("-", "_")
__version__ = package["version"]

_current_path = _os.path.dirname(_os.path.abspath(__file__))

_this_module = _sys.modules[__name__]

# One self-contained UMD bundle: emoji-mart, its full emoji data set and the
# React glue are all inside it, so there is nothing to fetch at runtime and no
# separate stylesheet — emoji-mart injects its own CSS from within the bundle.
#
# 0.0.x also registered an `async_resources` loop and a `.js.map` entry here.
# Neither did anything: no async chunks are produced, and Dash serves the map
# automatically when the browser asks for it.
_js_dist = [
    {
        "relative_package_path": "dash_emoji_mart.min.js",
        "namespace": package_name,
    }
]

_css_dist = []


for _component in __all__:
    setattr(locals()[_component], "_js_dist", _js_dist)
    setattr(locals()[_component], "_css_dist", _css_dist)
