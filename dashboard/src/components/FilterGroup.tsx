import { useI18n } from '../i18n/useI18n'
import type { MessageKey } from '../i18n/catalog/en'

/** One choice in the group. */
export interface FilterOption<T extends string> {
  value: T
  label: MessageKey
}

interface FilterGroupProps<T extends string> {
  /** What the group narrows the list by, named for the group of buttons. */
  label: string
  options: FilterOption<T>[]
  /** The chosen one. Compared to each option's value, so it must be one of them. */
  value: T
  onChange(value: T): void
}

/**
 * A small set of choices that narrows a list, as a row of pressed buttons.
 *
 * Segmented rather than a `<select>` because every choice fits on one line and
 * all of them stay visible. That matters when one of the options is the one worth
 * offering — "not served" on a delivery-price table is a question people ask, and
 * a dropdown hides that it is answerable at all.
 *
 * `aria-pressed` rather than a visual style alone, so the current choice is
 * announced as well as drawn. The buttons are in a `role="group"` with the label
 * as its accessible name, which is what ties the row together for a screen reader
 * instead of leaving three unrelated buttons.
 *
 * Generic over the option value so a caller keeps its own union and gets the
 * `onChange` narrowed to it, rather than casting a string back on the way out.
 */
export function FilterGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: FilterGroupProps<T>) {
  const { t } = useI18n()

  return (
    <div
      role="group"
      aria-label={label}
      className="mb-4 inline-flex flex-wrap gap-1 rounded-control border border-line bg-raised p-1"
    >
      {options.map((option) => {
        const active = option.value === value

        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={[
              'rounded px-3 py-1.5 text-xs font-medium transition-colors duration-150',
              active ? 'bg-accent-soft text-ink' : 'text-muted hover:bg-raised hover:text-ink',
            ].join(' ')}
          >
            {t(option.label)}
          </button>
        )
      })}
    </div>
  )
}