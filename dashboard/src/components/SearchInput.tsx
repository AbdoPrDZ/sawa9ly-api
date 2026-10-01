import { useId } from 'react'

import { useI18n } from '../i18n/useI18n'

/** Props for the search box that sits above a table. */
interface SearchInputProps {
  /** What is in the box, as the user types. */
  value: string
  /** Called on every keystroke. The caller debounces before fetching. */
  onChange: (value: string) => void
  /** Placeholder text, already translated by the caller. */
  placeholder: string
  /** Accessible label. Falls back to the placeholder when omitted. */
  label?: string
  /** True while a search is in flight, to show the wait. */
  busy?: boolean
  /** Extra classes for the wrapper, for placing it in a toolbar. */
  className?: string
}

/**
 * The text box above a list table.
 *
 * Deliberately uncontrolled by the server: it reports every keystroke and the
 * caller decides when to act, so the box stays responsive while the request
 * waits on the debounce in `useDebouncedSearch`.
 *
 * A `type="search"` rather than `type="text"`, which is what gives the browser's
 * own clear button in some engines, and `type="search"` is announced differently
 * by a screen reader.
 */
export function SearchInput({
  value,
  onChange,
  placeholder,
  label,
  busy = false,
  className = '',
}: SearchInputProps) {
  const id = useId()
  const { t } = useI18n()

  return (
    <div className={`relative ${className}`.trim()}>
      <label htmlFor={id} className="sr-only">
        {label || placeholder}
      </label>

      <input
        id={id}
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        aria-busy={busy}
        className="ps-3 pe-9"
      />

      {/* A clear button only while there is something to clear: an always-there
          disabled button is noise on an empty table. */}
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label={t('list.clearSearch')}
          className="absolute inset-y-0 end-1 my-auto flex h-6 w-6 items-center justify-center
                     rounded-full text-faint transition-colors duration-150
                     hover:bg-raised hover:text-ink"
        >
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          </svg>
        </button>
      )}
    </div>
  )
}