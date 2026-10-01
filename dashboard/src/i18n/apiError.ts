import { ApiError } from '../api/client'
import type { MessageKey } from './catalog/en'
import type { Translate } from './translations'

/** The status codes that mean the same thing to a reader whatever asked.
 *
 * Keyed on the status rather than on the server's wording, because the wording
 * is English and is not translated — see the docstring. `fallback` then covers
 * everything else, which is a per-page key because "could not load the products"
 * and "could not load your pages" are different sentences.
 */
const BY_STATUS: Record<number, MessageKey> = {
  401: 'error.signedOut',
  403: 'error.notAllowed',
  404: 'error.notFound',
  409: 'error.conflict',
  502: 'error.siteUnreachable',
  503: 'error.siteUnreachable',
  504: 'error.siteUnreachable',
}

/**
 * The sentence to show for a failed request, in the reader's language.
 *
 * **The server's own `detail` is deliberately not used.** It is written in English
 * and the API has no per-language messages, so showing it verbatim meant a user who
 * had picked French or Arabic was told "Product 9999 does not exist on
 * sawa9ly.app…" in English the moment anything went wrong. The English sentence is
 * still the right one — it names the id and says what to do — so the *status* is
 * translated here and the page supplies the wording through a key.
 *
 * What this gives up is the server's extra detail on a failure it described in
 * prose: a validation message, or a conflict that names the row. The full fix for
 * that is stable machine codes on API errors, which is a change to the API
 * contract and has not been made. Until then a specific sentence is available by
 * passing it as `fallback`, which is what the forms that want one do.
 */
export function apiErrorMessage(
  error: unknown,
  t: Translate,
  fallback: MessageKey,
): string {
  if (error instanceof ApiError) {
    const key = BY_STATUS[error.status]
    if (key) return t(key)
  }

  return t(fallback)
}
