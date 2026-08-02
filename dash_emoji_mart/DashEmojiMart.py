# AUTO GENERATED FILE - DO NOT EDIT

import typing  # noqa: F401
from typing_extensions import TypedDict, NotRequired, Literal # noqa: F401
from dash.development.base_component import Component, _explicitize_args
try:
    from dash.types import NumberType  # noqa: F401
except ImportError:
    # Backwards compatibility for dash<=4.1.0
    if typing.TYPE_CHECKING:
        raise
    NumberType = typing.Union[  # noqa: F401
        typing.SupportsFloat, typing.SupportsInt, typing.SupportsComplex
    ]

ComponentSingleType = typing.Union[str, int, float, Component, None]
ComponentType = typing.Union[
    ComponentSingleType,
    typing.Sequence[ComponentSingleType],
]


class DashEmojiMart(Component):
    """A DashEmojiMart component.
DashEmojiMart wraps the emoji-mart picker (https://github.com/missive/emoji-mart)
as a Dash component.

Selection is reported through two props, and callbacks may use either:

  * `value` — a plain string. `emoji.native` for a standard emoji ("😀"), or
    `emoji.src` for a custom one (the image URL). This is the 0.0.x contract
    and is unchanged.
  * `selectedEmoji` — the full emoji-mart object (id, name, native, unified,
    shortcodes, keywords, skin, src, ...), for callbacks that need more than
    the glyph. Added in 0.2.0.

Both are written in a single `setProps` call, so a callback with both as
Inputs fires once per pick rather than twice.

Keyword arguments:

- id (string | dict; optional):
    The ID used to identify this component in Dash callbacks.

- autoFocus (boolean; default False):
    Focus the search input when the picker mounts.

- categories (list; optional):
    Which categories to show, in order. Empty (the default) shows all
    of them. e.g. `[\"frequent\", \"people\", \"nature\"]`.

- categoryIcons (dict; optional):
    Icons for custom categories, keyed by category id. The value is
    inlined onto the matching entry in `custom` — typically an inline
    SVG string.

- className (string; optional):
    CSS class applied to the wrapper element around the picker.

- clickedOutside (number; default 0):
    Incremented once each time the user clicks outside the picker. Use
    it the way you would use `n_clicks` — for example to close a
    popover.  \"Outside\" means outside the component's wrapper
    element, so clicking an emoji, the search box or a category tab
    does NOT increment it. The click that opens the picker does not
    increment it either. Added in 0.2.0.

- custom (list; optional):
    Custom emoji categories. Each entry is `{id, name, emojis: [{id,
    name, keywords, skins: [{src}]}]}`.

- dynamicWidth (boolean; default False):
    Let the picker's width follow its container instead of `perLine`.

- emojiButtonColors (list; optional):
    Background colours cycled through on emoji hover/focus.

- emojiButtonRadius (string; default '100%'):
    Border radius of each emoji button. Default `\"100%\"`.

- emojiButtonSize (number; default 36):
    Size in px of each emoji button. Default 36.

- emojiSize (number; default 24):
    Size in px of the emoji inside its button. Default 24.

- emojiVersion (number; default 14):
    Maximum Emoji version to show. Default 14.

- exceptEmojis (list; optional):
    Emoji ids to hide from the grid, e.g. `[\"rage\", \"cry\"]`.  GRID
    ONLY — searching still finds them, for the same reason as
    `noCountryFlags`: both filters remove the emoji from its category
    while `SearchIndex.search` reads the unfiltered emoji map. Do not
    rely on this to keep a specific emoji away from a user.

- icons (string; default 'auto'):
    Category/search icon style: `\"auto\"`, `\"outline\"` or
    `\"solid\"`.

- locale (string; default 'en'):
    UI locale, e.g. `\"en\"`, `\"fr\"`, `\"de\"`, `\"ja\"`.

- maxFrequentRows (number; default 4):
    Rows reserved for frequently used emojis. Default 4.

- navPosition (string; default 'top'):
    Category nav position: `\"top\"`, `\"bottom\"` or `\"none\"`.

- noCountryFlags (boolean; default False):
    Hide country flags from the grid. Default False.  GRID ONLY —
    searching still finds them. This is an emoji-mart limitation,
    measured against 5.6.0: the filter runs while building each
    category and removes the emoji from `category.emojis`, but
    `SearchIndex.search` matches over `Object.values(Data.emojis)`,
    the unfiltered map, and applies no category filter of its own. So
    with this on, the flags category shrinks to a small safe list
    while typing \"united\" still returns the flags of the UK, US, UAE
    and the UN.  Not worked around here on purpose. emoji-mart loads
    its data into a module-global exactly once per page, so
    pre-filtering the data for one picker would silently change every
    other picker on the page and every page after it in a Dash SPA. A
    visible search result is better than an invisible,
    mount-order-dependent one.

- noResultsEmoji (string; default 'cry'):
    Emoji id shown when a search returns nothing. Default `\"cry\"`.

- perLine (number; default 9):
    Emojis per row. Default 9.

- persisted_props (list of a value equal to: 'value', 'selectedEmoji's; default ['value']):
    Properties whose value is persisted. Defaults to `[\"value\"]`.

- persistence (boolean | string | number; optional):
    Whether the picker's selection is persisted across browser
    sessions.

- persistence_type (a value equal to: 'local', 'session', 'memory'; default 'local'):
    Where persisted selections are stored: `\"local\"`, `\"session\"`
    or `\"memory\"`.

- previewEmoji (string; default 'point_up'):
    Emoji id shown in the idle preview. Default `\"point_up\"`.

- previewPosition (string; default 'bottom'):
    Preview position: `\"top\"`, `\"bottom\"` or `\"none\"`.

- searchPosition (string; default 'sticky'):
    Search bar position: `\"sticky\"`, `\"static\"` or `\"none\"`.

- selectedEmoji (dict; optional):
    The full emoji-mart object for the current selection — id, name,
    native, unified, shortcodes, keywords, skin and (for custom
    emojis) src. Set alongside `value` on every pick. Read-only. Added
    in 0.2.0.

- set (string; default 'native'):
    Emoji set: `\"native\"`, `\"apple\"`, `\"facebook\"`, `\"google\"`
    or `\"twitter\"`. Default `\"native\"`.

- skin (number; default 1):
    Default skin tone, 1 (lightest) to 6 (darkest). Default 1.

- skinTonePosition (string; default 'preview'):
    Skin-tone selector position: `\"preview\"`, `\"search\"` or
    `\"none\"`.

- theme (string; default 'auto'):
    Colour scheme: `\"auto\"`, `\"light\"` or `\"dark\"`.

- value (string; optional):
    The selected emoji as a string: the native glyph for a standard
    emoji (\"😀\"), or the image URL for a custom one. Read this in
    callbacks."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_emoji_mart'
    _type = 'DashEmojiMart'


    def __init__(
        self,
        id: typing.Optional[typing.Union[str, dict]] = None,
        value: typing.Optional[str] = None,
        selectedEmoji: typing.Optional[dict] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        custom: typing.Optional[typing.Sequence] = None,
        categoryIcons: typing.Optional[dict] = None,
        clickedOutside: typing.Optional[NumberType] = None,
        autoFocus: typing.Optional[bool] = None,
        categories: typing.Optional[typing.Sequence] = None,
        dynamicWidth: typing.Optional[bool] = None,
        emojiButtonColors: typing.Optional[typing.Sequence] = None,
        emojiButtonRadius: typing.Optional[str] = None,
        emojiButtonSize: typing.Optional[NumberType] = None,
        emojiSize: typing.Optional[NumberType] = None,
        emojiVersion: typing.Optional[NumberType] = None,
        exceptEmojis: typing.Optional[typing.Sequence] = None,
        icons: typing.Optional[str] = None,
        locale: typing.Optional[str] = None,
        maxFrequentRows: typing.Optional[NumberType] = None,
        navPosition: typing.Optional[str] = None,
        noCountryFlags: typing.Optional[bool] = None,
        noResultsEmoji: typing.Optional[str] = None,
        perLine: typing.Optional[NumberType] = None,
        previewEmoji: typing.Optional[str] = None,
        previewPosition: typing.Optional[str] = None,
        searchPosition: typing.Optional[str] = None,
        set: typing.Optional[str] = None,
        skin: typing.Optional[NumberType] = None,
        skinTonePosition: typing.Optional[str] = None,
        theme: typing.Optional[str] = None,
        persistence: typing.Optional[typing.Union[bool, str, NumberType]] = None,
        persisted_props: typing.Optional[typing.Sequence[Literal["value", "selectedEmoji"]]] = None,
        persistence_type: typing.Optional[Literal["local", "session", "memory"]] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'autoFocus', 'categories', 'categoryIcons', 'className', 'clickedOutside', 'custom', 'dynamicWidth', 'emojiButtonColors', 'emojiButtonRadius', 'emojiButtonSize', 'emojiSize', 'emojiVersion', 'exceptEmojis', 'icons', 'locale', 'maxFrequentRows', 'navPosition', 'noCountryFlags', 'noResultsEmoji', 'perLine', 'persisted_props', 'persistence', 'persistence_type', 'previewEmoji', 'previewPosition', 'searchPosition', 'selectedEmoji', 'set', 'skin', 'skinTonePosition', 'style', 'theme', 'value']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'autoFocus', 'categories', 'categoryIcons', 'className', 'clickedOutside', 'custom', 'dynamicWidth', 'emojiButtonColors', 'emojiButtonRadius', 'emojiButtonSize', 'emojiSize', 'emojiVersion', 'exceptEmojis', 'icons', 'locale', 'maxFrequentRows', 'navPosition', 'noCountryFlags', 'noResultsEmoji', 'perLine', 'persisted_props', 'persistence', 'persistence_type', 'previewEmoji', 'previewPosition', 'searchPosition', 'selectedEmoji', 'set', 'skin', 'skinTonePosition', 'style', 'theme', 'value']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(DashEmojiMart, self).__init__(**args)

setattr(DashEmojiMart, "__init__", _explicitize_args(DashEmojiMart.__init__))
