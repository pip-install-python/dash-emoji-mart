"""What this site is actually running — read from the installed packages, not hard-coded."""

import dash
import dash_mantine_components as dmc

import dash_emoji_mart
from lib.constants import EMOJI_MART_VERSION


def _row(label, value):
    return dmc.TableTr([dmc.TableTd(label), dmc.TableTd(dmc.Code(value))])


component = dmc.Table(
    [
        dmc.TableThead(
            dmc.TableTr([dmc.TableTh("Package"), dmc.TableTh("Version")])
        ),
        dmc.TableTbody(
            [
                _row("dash-emoji-mart", dash_emoji_mart.__version__),
                _row("emoji-mart (bundled)", EMOJI_MART_VERSION),
                _row("dash", dash.__version__),
                _row("components", ", ".join(dash_emoji_mart.__all__)),
            ]
        ),
    ],
    striped=True,
    withTableBorder=True,
)
