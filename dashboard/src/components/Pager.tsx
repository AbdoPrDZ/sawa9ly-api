import { useI18n } from '../i18n/useI18n'

/** Props for the controls under a paged table. */
interface PagerProps {
  /** How many rows match in total, across every page. */
  total: number
  /** Zero-based index of the page on screen. */
  page: number
  /** How many rows were asked for. */
  pageSize: number
  /** Whether the server says anything is after this page. */
  hasMore: boolean
  /** Called with the zero-based page to show. */
  onPage: (page: number) => void
}

/**
 * Previous/next and a count, for a table the server is paging.
 *
 * Only two page controls, not a row of numbered ones. There is no reason to jump
 * to page 7 of 400 from a table of 50 rows, and a full set of numbers goes wrong
 * the moment a row is deleted. The count is the honest one — "51–100 of 340", so
 * the user can tell a filtered table from an unfiltered one, which "51–100" alone
 * cannot.
 *
 * A single-page result says so outright rather than showing dead controls.
 *
 * `hasMore` comes from the server rather than being derived from a short page,
 * because a page can be short for a reason other than being the last one — a row
 * deleted between two requests would otherwise strand the user on a page they can
 * only go back from.
 */
export function Pager({ total, page, pageSize, hasMore, onPage }: PagerProps) {
  const { t } = useI18n()

  if (total === 0) return null

  const from = page * pageSize + 1
  const to = Math.min(total, (page + 1) * pageSize)
  const pages = Math.ceil(total / pageSize)
  const single = pages <= 1

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-1 py-3 text-sm">
      <p className="text-muted tabular-nums">
        {single ? t('list.onePage', { total }) : t('list.showing', { from, to, total })}
      </p>

      {!single && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onPage(page - 1)}
            disabled={page === 0}
            className="rounded-control border border-line bg-raised px-3 py-1.5 text-xs
                       font-medium text-ink transition-colors duration-150
                       hover:border-line-strong disabled:cursor-not-allowed disabled:opacity-40"
          >
            {t('list.previous')}
          </button>

          <span className="px-1 text-muted tabular-nums">{t('list.page', { page: page + 1, pages })}</span>

          <button
            type="button"
            onClick={() => onPage(page + 1)}
            disabled={!hasMore}
            className="rounded-control border border-line bg-raised px-3 py-1.5 text-xs
                       font-medium text-ink transition-colors duration-150
                       hover:border-line-strong disabled:cursor-not-allowed disabled:opacity-40"
          >
            {t('list.next')}
          </button>
        </div>
      )}
    </div>
  )
}