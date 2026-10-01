import { useI18n } from '../i18n/useI18n'
import type { MessageKey } from '../i18n/catalog/en'

/** Placeholder while a page's data is in flight.
 *
 * A rotating ring rather than a bare line of text, because the whole point is to
 * be noticed without being read. It is the one animation on the page that loops,
 * and it stops the moment the data does.
 */
export function Spinner({ label }: { label: string }) {
  return (
    <div
      className="flex items-center justify-center gap-2.5 py-10 text-sm text-muted"
      role="status"
    >
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-4 w-4 animate-spin">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
        <path
          d="M21 12a9 9 0 0 0-9-9"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
      <span>{label}</span>
    </div>
  )
}

/** A spinner whose label comes from the catalogue.
 *
 * Typed on `MessageKey` so the key is checked, and so `t` gets the narrow
 * signature that requires the fields a key actually needs — `loading.order`
 * without `{id}` is a build error rather than a sentence with a hole in it.
 */
export function MessageSpinner({
  messageKey,
  fields,
}: {
  messageKey: MessageKey
  fields?: Record<string, string | number>
}) {
  const { t } = useI18n()

  return <Spinner label={t(messageKey, fields)} />
}
