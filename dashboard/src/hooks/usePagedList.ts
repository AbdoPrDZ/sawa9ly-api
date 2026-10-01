import { useCallback, useEffect, useRef, useState } from 'react'

import { isUnauthorized } from '../api/client'
import type { ListQuery, PageResult } from '../api/types'
import { apiErrorMessage } from '../i18n/apiError'
import type { MessageKey } from '../i18n/catalog/en'
import { useI18n } from '../i18n/useI18n'
import { useListQuery } from './useListQuery'
import type { ListQueryState } from './useListQuery'

/**
 * How many rows a list screen asks for.
 *
 * Mirrors `DEFAULT_PAGE_SIZE` in `src/models/paging.py`. Comfortably more than
 * fits on a large screen, so most users never turn the page, and well under the
 * server's cap of 200.
 */
export const PAGE_SIZE = 50

/** Everything a list screen needs to render itself. */
export interface PagedList<T> {
  /** The rows on this page, or null while the first load is still out. */
  items: T[] | null
  /** How many rows match the current search, across every page. */
  total: number
  /** Whether the server says anything is after this page. */
  hasMore: boolean
  /** True while any request is in flight. */
  busy: boolean
  /** The last failure, already translated, or `''`. */
  error: string
  /** The search box and pager state, to hand to `SearchInput` and `Pager`. */
  query: ListQueryState
  /** Fetch again with the same search and page. */
  reload: () => void
  /** Put a message up, e.g. after a create or a delete. */
  setError: (message: string) => void
}

/** Optional setup for `usePagedList`. */
interface PagedListOptions {
  /** Catalogue key for the failure, e.g. `error.orders`. */
  errorKey: MessageKey
  /** Called instead of showing an error when the caller is no longer allowed. */
  onUnauthorized?: () => void
  /**
   * Changes when the caller wants a different fetcher used, e.g. the string
   * `'admin'` when a `super` starts watching everyone's orders.
   *
   * The fetcher itself cannot be the trigger, because it is normally an inline
   * arrow and its identity changes on every render — depending on it would
   * reload for ever. This is the caller's explicit statement that the choice of
   * list actually changed.
   */
  fetcherKey?: string
}

/**
 * A server-paged, server-searched list, and everything that goes with it.
 *
 * Owns the loading, the error, the search box and the pager, because those five
 * things are the same in all six list screens and were being copied into each.
 *
 * **The stale-response guard is the reason this is a hook and not six copies of
 * a `useEffect`.** Typing "sawa" issues a request after the debounce; typing it
 * faster than the server answers can leave two in flight, and the slower one can
 * land last and overwrite the newer rows with older ones. Every load takes a
 * number, and a result is only applied if it is still the newest. Without that
 * the table shows results for a prefix of what was typed, and nothing looks
 * broken, which is the worst kind of wrong.
 *
 * `fetcher` is read through a ref rather than depended on, so a caller may pass
 * an inline arrow — switching between an admin's and a user's orders, say —
 * without every render triggering a reload.
 */
export function usePagedList<T>(
  fetcher: (query: ListQuery) => Promise<PageResult<T>>,
  { errorKey, onUnauthorized, fetcherKey }: PagedListOptions,
): PagedList<T> {
  const { t } = useI18n()
  const query = useListQuery()

  const [page, setPage] = useState<PageResult<T> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [nonce, setNonce] = useState(0)

  const latest = useRef(0)
  const fetcherRef = useRef(fetcher)
  const optionsRef = useRef({ errorKey, onUnauthorized, t })

  fetcherRef.current = fetcher
  optionsRef.current = { errorKey, onUnauthorized, t }

  const { q, page: current, setTerm, setPage: goToPage } = query

  useEffect(() => {
    const ticket = latest.current + 1
    latest.current = ticket

    setBusy(true)

    fetcherRef.current({ q, limit: PAGE_SIZE, offset: current * PAGE_SIZE })
      .then((result) => {
        if (latest.current !== ticket) return
        setPage(result)
        setError('')
      })
      .catch((caught: unknown) => {
        if (latest.current !== ticket) return

        const { onUnauthorized: gate } = optionsRef.current

        if (isUnauthorized(caught)) {
          gate?.()
        } else {
          setError(apiErrorMessage(caught, optionsRef.current.t, optionsRef.current.errorKey))
        }
      })
      .finally(() => {
        if (latest.current === ticket) setBusy(false)
      })
  // `fetcherKey` is in the dependencies, not `fetcher`. Without it, a caller
    // that swaps the fetcher on a changing value — Orders choosing between the
    // user's own orders and the admin's — would keep showing whichever list it
    // first fetched, with no reload to trigger the change.
  }, [q, current, nonce, fetcherKey])

  const reload = useCallback(() => setNonce((value) => value + 1), [])

  return {
    items: page?.items ?? null,
    total: page?.total ?? 0,
    hasMore: page?.has_more ?? false,
    busy,
    error,
    query: { ...query, setTerm, setPage: goToPage },
    reload,
    setError,
  }
}