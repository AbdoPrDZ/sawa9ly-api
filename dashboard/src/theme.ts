/** Which theme the dashboard is in, and where that choice is kept.
 *
 * The theme is an attribute on the document element rather than a React value,
 * because the stylesheet has to be able to read it: the palette in
 * `src/styles.css` is a pair of `:root` blocks and a live `var()` binding, so
 * flipping `data-theme` repaints the page without React re-rendering anything.
 *
 * That also means the choice has to survive a reload, and it has to be applied
 * before the first paint — hence localStorage, and the small inline script in
 * `index.html` that sets the attribute before the stylesheet is applied. A theme
 * that arrives after paint is a white flash on every load, which is worse than
 * having no switch at all.
 *
 * **The storage key is written out in two places**: here, and in that inline
 * script, which cannot import anything. They have to agree, the same way
 * `DASHBOARD_BASE`, `base` in `vite.config.ts` and `BASENAME` do.
 */
export type Theme = 'dark' | 'light'

/** Dark unless the stored value says otherwise. */
export const DEFAULT_THEME: Theme = 'dark'

const KEY = 'sawa9ly.dashboard.theme'

function isTheme(value: unknown): value is Theme {
  return value === 'dark' || value === 'light'
}

/** The stored theme, or the default when there is nothing usable stored. */
export function read(): Theme {
  const stored = localStorage.getItem(KEY)
  return isTheme(stored) ? stored : DEFAULT_THEME
}

/** Put the theme on the document and remember it.
 *
 * A storage failure is not worth handling: the attribute is already set by then,
 * so the page is already in the chosen theme and the only thing lost is the
 * memory of it.
 */
export function apply(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(KEY, theme)
}
