import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import PropTypes from 'prop-types';
import Picker from '@emoji-mart/react';
import data from '@emoji-mart/data';

// `theme="auto"` follows the APP, then the OS — in that order.
//
// emoji-mart's own "auto" reads `prefers-color-scheme` and nothing else. In a
// Dash app that is the wrong signal: almost every one of them ships a theme
// toggle, and the toggle does not touch the OS. Flip a Dash Mantine
// Components app to light on a machine set to dark and every picker in it
// stays dark, against a white page. Nothing errors, and it looks like the
// component ignoring its own `theme` prop.
//
// The fix is to prefer an explicit app-level colour scheme when the document
// advertises one. `data-mantine-color-scheme` on <html> is what DMC sets, and
// reading an attribute creates no dependency on DMC — an app that does not use
// it simply falls through to the media query, which is emoji-mart's behaviour
// unchanged.
//
// DMC writes "auto" into that attribute when it is itself following the
// system, so "auto" there has to fall through rather than be taken literally.
const APP_SCHEME_ATTR = 'data-mantine-color-scheme';

const resolveAutoTheme = () => {
    if (typeof document === 'undefined') {
        return 'light';
    }
    const declared = document.documentElement.getAttribute(APP_SCHEME_ATTR);
    if (declared === 'light' || declared === 'dark') {
        return declared;
    }
    return typeof window !== 'undefined' &&
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
};

/**
 * The concrete 'light' | 'dark' to hand emoji-mart.
 *
 * An explicit `theme` is passed straight through — this only resolves "auto",
 * and it re-resolves when either signal changes, so a toggle takes effect
 * without a remount.
 */
const useResolvedTheme = (theme) => {
    const [resolved, setResolved] = useState(() =>
        theme === 'auto' ? resolveAutoTheme() : theme
    );

    useEffect(() => {
        if (theme !== 'auto') {
            setResolved(theme);
            return undefined;
        }
        if (typeof document === 'undefined') {
            return undefined;
        }

        const sync = () => setResolved(resolveAutoTheme());
        sync();

        // The app's toggle: an attribute flip on <html>, no event to listen for.
        const observer = new MutationObserver(sync);
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: [APP_SCHEME_ATTR],
        });

        // The OS preference, which still decides when no app scheme is set.
        const media =
            typeof window !== 'undefined' && window.matchMedia
                ? window.matchMedia('(prefers-color-scheme: dark)')
                : null;
        if (media) {
            // Safari < 14 has no addEventListener on MediaQueryList.
            if (media.addEventListener) {
                media.addEventListener('change', sync);
            } else if (media.addListener) {
                media.addListener(sync);
            }
        }

        return () => {
            observer.disconnect();
            if (media) {
                if (media.removeEventListener) {
                    media.removeEventListener('change', sync);
                } else if (media.removeListener) {
                    media.removeListener(sync);
                }
            }
        };
    }, [theme]);

    return resolved;
};

// Custom-emoji images, sized so that dimensionless SVGs are not invisible.
//
// emoji-mart renders a custom emoji as `<img style="max-width: Npx;
// max-height: Npx">` — a MAXIMUM and nothing else. A raster source (.png, .gif)
// has intrinsic dimensions, so it scales down to N and shows. An SVG whose root
// element carries only a `viewBox` and no `width`/`height` has NO intrinsic
// size, so `width: auto` under a bare max-width resolves to 0 and the emoji
// renders as a 0x0 box: present in the DOM, focusable, clickable, invisible.
//
// That is why the failure looks arbitrary rather than systematic — one custom
// category renders and the next is blank, depending only on what the author
// happened to link. Iconify's API SVGs ship `width="1em" height="1em"` and are
// fine; raw SVGs straight off a repo (devicons and most icon projects) are not.
//
// `1em` is the size emoji-mart itself intends: it sets font-size to `emojiSize`
// on each grid button and to the larger preview size in the footer, so one rule
// lands correctly in both places without knowing either number. `object-fit`
// keeps non-square artwork undistorted, and the inline `max-*` still clamps.
//
// It goes in the shadow root because that is where the picker lives — no
// page-level stylesheet, and no `className`/`style` on our wrapper, can reach
// inside it.
const SHADOW_CSS = `
.emoji-mart-emoji img {
    width: 1em;
    height: 1em;
    object-fit: contain;
}
`;

const SHADOW_CSS_FLAG = '_dashEmojiMartSized';

/**
 * Apply SHADOW_CSS to a picker's shadow root, once.
 *
 * Returns true when the sheet is in place (or already was), false when the
 * custom element has not upgraded yet and the caller should retry.
 */
const applyShadowCss = (host) => {
    const root = host && host.shadowRoot;
    if (!root) {
        return false;
    }
    if (root[SHADOW_CSS_FLAG]) {
        return true;
    }

    // Constructable stylesheets where available; a <style> node is the fallback
    // for anything that does not support adoptedStyleSheets.
    try {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync(SHADOW_CSS);
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
    } catch (e) {
        const style = document.createElement('style');
        style.textContent = SHADOW_CSS;
        root.appendChild(style);
    }

    root[SHADOW_CSS_FLAG] = true;
    return true;
};

/**
 * DashEmojiMart wraps the emoji-mart picker (https://github.com/missive/emoji-mart)
 * as a Dash component.
 *
 * Selection is reported through two props, and callbacks may use either:
 *
 *   * `value` — a plain string. `emoji.native` for a standard emoji ("😀"), or
 *     `emoji.src` for a custom one (the image URL). This is the 0.0.x contract
 *     and is unchanged.
 *   * `selectedEmoji` — the full emoji-mart object (id, name, native, unified,
 *     shortcodes, keywords, skin, src, ...), for callbacks that need more than
 *     the glyph. Added in 0.2.0.
 *
 * Both are written in a single `setProps` call, so a callback with both as
 * Inputs fires once per pick rather than twice.
 */
const DashEmojiMart = ({
    id,
    setProps,
    value,
    selectedEmoji,
    className,
    style,
    custom = [],
    autoFocus = false,
    categories = [],
    categoryIcons = {},
    dynamicWidth = false,
    emojiButtonColors = [],
    emojiButtonRadius = '100%',
    emojiButtonSize = 36,
    emojiSize = 24,
    emojiVersion = 14,
    exceptEmojis = [],
    icons = 'auto',
    locale = 'en',
    maxFrequentRows = 4,
    navPosition = 'top',
    noCountryFlags = false,
    noResultsEmoji = 'cry',
    perLine = 9,
    previewEmoji = 'point_up',
    previewPosition = 'bottom',
    searchPosition = 'sticky',
    set = 'native',
    skin = 1,
    skinTonePosition = 'preview',
    theme = 'auto',
    clickedOutside = 0,
}) => {
    // `categoryIcons` is keyed by custom-category id; emoji-mart wants the icon
    // inlined on the category itself. Only build the array when there is
    // something to build — passing `custom: []` makes emoji-mart render an
    // empty extra nav slot.
    const customCategories = useMemo(
        () =>
            custom && custom.length > 0
                ? custom.map((category) => ({
                      ...category,
                      icon: categoryIcons[category.id],
                  }))
                : undefined,
        [custom, categoryIcons]
    );

    const handleEmojiSelect = useCallback(
        (emoji) => {
            if (!setProps) {
                return;
            }
            // Custom emojis carry `src` (an image URL) and no `native` glyph.
            setProps({
                value: emoji.src ? emoji.src : emoji.native,
                selectedEmoji: emoji,
            });
        },
        [setProps]
    );

    // Outside-click detection, deliberately NOT emoji-mart's own.
    //
    // emoji-mart's `onClickOutside` is a document-level listener that fires
    // whenever `event.target !== <the picker root element>`. Two consequences
    // make it unusable as a Dash signal:
    //
    //   1. Clicking an EMOJI fires it. The target is the emoji button, which is
    //      a descendant of the root rather than the root itself, so the
    //      inequality holds and "clicked outside" is reported for a click that
    //      was plainly inside.
    //   2. The click that MOUNTS the picker fires it. emoji-mart registers its
    //      listener during mount, and a `document` listener added while a click
    //      is still bubbling toward `document` still receives that same click.
    //      So a picker opened from a button reports an outside click before the
    //      user has clicked anything — which made the popover pattern close
    //      itself the instant it opened.
    //
    // Instead: our own listener, containment-tested against the wrapper, and
    // attached one task later so the opening click has finished dispatching.
    // Resolved here rather than handed to emoji-mart as "auto" — see
    // useResolvedTheme above for why the media query alone is the wrong signal.
    const resolvedTheme = useResolvedTheme(theme);

    const wrapperRef = useRef(null);
    // Refs, so the effect binds once instead of re-binding on every count
    // change (which would reintroduce the mid-dispatch problem).
    const setPropsRef = useRef(setProps);
    const clickedOutsideRef = useRef(clickedOutside || 0);
    setPropsRef.current = setProps;
    clickedOutsideRef.current = clickedOutside || 0;

    useEffect(() => {
        if (typeof document === 'undefined') {
            return undefined;
        }
        let detach = null;
        const timer = setTimeout(() => {
            const onDocumentClick = (event) => {
                const node = wrapperRef.current;
                if (node && event.target && node.contains(event.target)) {
                    return;
                }
                if (setPropsRef.current) {
                    setPropsRef.current({
                        clickedOutside: clickedOutsideRef.current + 1,
                    });
                }
            };
            document.addEventListener('click', onDocumentClick);
            detach = () => document.removeEventListener('click', onDocumentClick);
        }, 0);

        return () => {
            clearTimeout(timer);
            if (detach) {
                detach();
            }
        };
    }, []);

    // Style the shadow root once <em-emoji-picker> has upgraded. @emoji-mart/react
    // creates the element in its own effect and the custom element attaches its
    // shadow root during that upgrade, so the root is usually there by the time
    // this parent effect runs — but "usually" is not "always" (the definition is
    // registered lazily), hence the bounded retry rather than a single attempt.
    useEffect(() => {
        if (typeof document === 'undefined') {
            return undefined;
        }
        let attempts = 0;
        let timer = null;
        const attempt = () => {
            const host =
                wrapperRef.current &&
                wrapperRef.current.querySelector('em-emoji-picker');
            if (applyShadowCss(host)) {
                return;
            }
            attempts += 1;
            if (attempts < 20) {
                timer = setTimeout(attempt, 50);
            }
        };
        attempt();
        return () => {
            if (timer) {
                clearTimeout(timer);
            }
        };
        // `set` and `locale` make emoji-mart rebuild, and a changed `custom`
        // remounts the picker in practice — re-check on each so a fresh shadow
        // root never goes unstyled.
    }, [set, locale, custom]);

    // Make `dynamicWidth` actually widen the picker.
    //
    // emoji-mart implements the option by setting `width: 100%` on a <section>
    // INSIDE its shadow root, and never touches the <em-emoji-picker> host. The
    // host is a custom element, so it has no author width of its own and sizes
    // to its content — and its content is the section asking for 100% of the
    // host. The constraint is circular and resolves at min-content, so turning
    // the option on made the picker COLLAPSE (measured: 532px -> 216px inside a
    // 482px parent) instead of filling anything, and the grid reflowed under
    // the pointer while hovering.
    //
    // Sizing the host is the missing half, and it has to happen out here: the
    // host is in the light DOM, so no shadow stylesheet can reach it, and the
    // wrapper `className`/`style` props apply to our own div rather than to it.
    //
    // The container still needs a width for "100%" to mean something — a
    // shrink-to-fit flex item gives 100% of nothing. That is the caller's
    // layout, and docs/configuration/example.py shows it.
    useEffect(() => {
        const host =
            wrapperRef.current &&
            wrapperRef.current.querySelector('em-emoji-picker');
        if (!host) {
            return;
        }
        if (dynamicWidth) {
            host.style.width = '100%';
        } else {
            host.style.removeProperty('width');
        }
    }, [dynamicWidth, set, locale, custom]);

    const pickerProps = {
        data,
        onEmojiSelect: handleEmojiSelect,
        // `onClickOutside` is deliberately not passed — see the useEffect above.
        autoFocus,
        dynamicWidth,
        emojiButtonColors:
            emojiButtonColors.length > 0 ? emojiButtonColors : undefined,
        emojiButtonRadius,
        emojiButtonSize,
        emojiSize,
        emojiVersion,
        exceptEmojis: exceptEmojis.length > 0 ? exceptEmojis : undefined,
        icons,
        locale,
        maxFrequentRows,
        navPosition,
        noCountryFlags,
        noResultsEmoji,
        perLine,
        previewEmoji,
        previewPosition,
        searchPosition,
        set,
        skin,
        skinTonePosition,
        theme: resolvedTheme,
    };

    if (customCategories) {
        pickerProps.custom = customCategories;
    }

    // An empty `categories` means "all of them"; passing [] hides every one.
    if (categories && categories.length > 0) {
        pickerProps.categories = categories;
    }

    return (
        <div id={id} className={className} style={style} ref={wrapperRef}>
            <Picker {...pickerProps} />
        </div>
    );
};

DashEmojiMart.propTypes = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),

    /**
     * The selected emoji as a string: the native glyph for a standard emoji
     * ("😀"), or the image URL for a custom one. Read this in callbacks.
     */
    value: PropTypes.string,

    /**
     * The full emoji-mart object for the current selection — id, name, native,
     * unified, shortcodes, keywords, skin and (for custom emojis) src. Set
     * alongside `value` on every pick. Read-only. Added in 0.2.0.
     */
    selectedEmoji: PropTypes.object,

    /**
     * CSS class applied to the wrapper element around the picker.
     */
    className: PropTypes.string,

    /**
     * Inline styles applied to the wrapper element around the picker.
     */
    style: PropTypes.object,

    /**
     * Custom emoji categories. Each entry is
     * `{id, name, emojis: [{id, name, keywords, skins: [{src}]}]}`.
     */
    custom: PropTypes.array,

    /**
     * Icons for custom categories, keyed by category id. The value is inlined
     * onto the matching entry in `custom` — typically an inline SVG string.
     */
    categoryIcons: PropTypes.object,

    /**
     * Incremented once each time the user clicks outside the picker. Use it the
     * way you would use `n_clicks` — for example to close a popover.
     *
     * "Outside" means outside the component's wrapper element, so clicking an
     * emoji, the search box or a category tab does NOT increment it. The click
     * that opens the picker does not increment it either. Added in 0.2.0.
     */
    clickedOutside: PropTypes.number,

    /**
     * Focus the search input when the picker mounts.
     */
    autoFocus: PropTypes.bool,

    /**
     * Which categories to show, in order. Empty (the default) shows all of
     * them. e.g. `["frequent", "people", "nature"]`.
     */
    categories: PropTypes.array,

    /**
     * Let the picker's width follow its container instead of `perLine`.
     */
    dynamicWidth: PropTypes.bool,

    /**
     * Background colours cycled through on emoji hover/focus.
     */
    emojiButtonColors: PropTypes.array,

    /**
     * Border radius of each emoji button. Default `"100%"`.
     */
    emojiButtonRadius: PropTypes.string,

    /**
     * Size in px of each emoji button. Default 36.
     */
    emojiButtonSize: PropTypes.number,

    /**
     * Size in px of the emoji inside its button. Default 24.
     */
    emojiSize: PropTypes.number,

    /**
     * Maximum Emoji version to show. Default 14.
     */
    emojiVersion: PropTypes.number,

    /**
     * Emoji ids to hide from the grid, e.g. `["rage", "cry"]`.
     *
     * GRID ONLY — searching still finds them, for the same reason as
     * `noCountryFlags`: both filters remove the emoji from its category while
     * `SearchIndex.search` reads the unfiltered emoji map. Do not rely on this
     * to keep a specific emoji away from a user.
     */
    exceptEmojis: PropTypes.array,

    /**
     * Category/search icon style: `"auto"`, `"outline"` or `"solid"`.
     */
    icons: PropTypes.string,

    /**
     * UI locale, e.g. `"en"`, `"fr"`, `"de"`, `"ja"`.
     */
    locale: PropTypes.string,

    /**
     * Rows reserved for frequently used emojis. Default 4.
     */
    maxFrequentRows: PropTypes.number,

    /**
     * Category nav position: `"top"`, `"bottom"` or `"none"`.
     */
    navPosition: PropTypes.string,

    /**
     * Hide country flags from the grid. Default False.
     *
     * GRID ONLY — searching still finds them. This is an emoji-mart
     * limitation, measured against 5.6.0: the filter runs while building each
     * category and removes the emoji from `category.emojis`, but
     * `SearchIndex.search` matches over `Object.values(Data.emojis)`, the
     * unfiltered map, and applies no category filter of its own. So with this
     * on, the flags category shrinks to a small safe list while typing
     * "united" still returns the flags of the UK, US, UAE and the UN.
     *
     * Not worked around here on purpose. emoji-mart loads its data into a
     * module-global exactly once per page, so pre-filtering the data for one
     * picker would silently change every other picker on the page and every
     * page after it in a Dash SPA. A visible search result is better than an
     * invisible, mount-order-dependent one.
     */
    noCountryFlags: PropTypes.bool,

    /**
     * Emoji id shown when a search returns nothing. Default `"cry"`.
     */
    noResultsEmoji: PropTypes.string,

    /**
     * Emojis per row. Default 9.
     */
    perLine: PropTypes.number,

    /**
     * Emoji id shown in the idle preview. Default `"point_up"`.
     */
    previewEmoji: PropTypes.string,

    /**
     * Preview position: `"top"`, `"bottom"` or `"none"`.
     */
    previewPosition: PropTypes.string,

    /**
     * Search bar position: `"sticky"`, `"static"` or `"none"`.
     */
    searchPosition: PropTypes.string,

    /**
     * Emoji set: `"native"`, `"apple"`, `"facebook"`, `"google"` or
     * `"twitter"`. Default `"native"`.
     */
    set: PropTypes.string,

    /**
     * Default skin tone, 1 (lightest) to 6 (darkest). Default 1.
     */
    skin: PropTypes.number,

    /**
     * Skin-tone selector position: `"preview"`, `"search"` or `"none"`.
     */
    skinTonePosition: PropTypes.string,

    /**
     * Colour scheme: `"auto"`, `"light"` or `"dark"`.
     */
    theme: PropTypes.string,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func,

    /**
     * Whether the picker's selection is persisted across browser sessions.
     */
    persistence: PropTypes.oneOfType([
        PropTypes.bool,
        PropTypes.string,
        PropTypes.number,
    ]),

    /**
     * Properties whose value is persisted. Defaults to `["value"]`.
     */
    persisted_props: PropTypes.arrayOf(
        PropTypes.oneOf(['value', 'selectedEmoji'])
    ),

    /**
     * Where persisted selections are stored: `"local"`, `"session"` or
     * `"memory"`.
     */
    persistence_type: PropTypes.oneOf(['local', 'session', 'memory']),
};

DashEmojiMart.defaultProps = {
    persisted_props: ['value'],
    persistence_type: 'local',
};

export default DashEmojiMart;
