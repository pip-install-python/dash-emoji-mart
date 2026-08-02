"""A reaction bar: three message rows, each with its own popover-mounted picker.

Every picker shares one set of pattern-matching callbacks via MATCH, so adding a fourth
row would need no new callback code.

There is deliberately NO callback on the trigger. `dmc.Popover` wraps whatever you put
in `PopoverTarget` in a Box with its own `onClick` that writes `opened = not opened`, so
opening is already handled client-side — a Python `toggle` callback on top of that reads
the ALREADY-flipped `opened` as State and flips it straight back, and the popover never
opens. Closing on pick is the only thing left to wire up.
"""

import dash_mantine_components as dmc
from dash import MATCH, Input, Output, callback
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from dash_emoji_mart import DashEmojiMart

MESSAGES = [
    (1, "Ada", "Shipped the 0.2.0 tag — CI is green across the whole Dash 4 matrix."),
    (2, "Grace", "Docs site is live at emojimart.2plot.dev."),
    (3, "Alan", "The popover pattern is the one people keep asking for."),
]


def reaction_row(index, author, text):
    return dmc.Paper(
        dmc.Group(
            [
                dmc.Stack(
                    [
                        dmc.Text(author, fw=600, size="sm"),
                        dmc.Text(text, size="sm", c="dimmed"),
                    ],
                    gap=2,
                    style={"flex": 1},
                ),
                dmc.Group(
                    [
                        dmc.Text(
                            id={"type": "reaction-out", "index": index},
                            children="",
                            style={"fontSize": 24, "minWidth": 32},
                        ),
                        dmc.Popover(
                            [
                                dmc.PopoverTarget(
                                    dmc.ActionIcon(
                                        DashIconify(
                                            icon="tabler:mood-plus", width=18
                                        ),
                                        id={"type": "reaction-trigger", "index": index},
                                        variant="light",
                                        size="lg",
                                    )
                                ),
                                dmc.PopoverDropdown(
                                    DashEmojiMart(
                                        id={"type": "reaction-picker", "index": index},
                                        perLine=8,
                                        emojiSize=22,
                                        maxFrequentRows=1,
                                        previewPosition="none",
                                        skinTonePosition="search",
                                    ),
                                    p=0,
                                ),
                            ],
                            id={"type": "reaction-popover", "index": index},
                            opened=False,
                            position="bottom-end",
                            withArrow=True,
                            shadow="md",
                            # Explicit, not decorative. keepMounted=True would
                            # mount all three pickers — each one a full emoji
                            # dataset and ~1500 buttons — on page load, for
                            # three popovers the reader may never open.
                            keepMounted=False,
                        ),
                    ],
                    gap="sm",
                ),
            ],
            justify="space-between",
            wrap="nowrap",
        ),
        withBorder=True,
        p="md",
        radius="md",
    )


component = dmc.Stack(
    [reaction_row(i, author, text) for i, author, text in MESSAGES],
    gap="sm",
)


@callback(
    Output({"type": "reaction-out", "index": MATCH}, "children"),
    Output({"type": "reaction-popover", "index": MATCH}, "opened"),
    Output({"type": "reaction-picker", "index": MATCH}, "value"),
    Input({"type": "reaction-picker", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def pick(value):
    """Set the reaction, close the popover, and clear the picker's `value`.

    Dismissing without picking needs no callback at all — that is Mantine's own
    closeOnClickOutside/closeOnEscape, routed through the Popover's onChange into
    setProps({opened: False}).

    The third output is what makes picking the SAME emoji twice work. `value` is not
    reset by closing the popover (unmounting the picker does not clear the prop in
    Dash's store), so a second identical pick writes an unchanged `value`, Dash sees
    no change, and nothing fires — the popover just sits there open. Clearing it here
    means the next pick is always a change. The guard below is what stops that clearing
    write from re-entering this callback and blanking the reaction we just set.
    """
    if not value:
        raise PreventUpdate
    return value, False, None
