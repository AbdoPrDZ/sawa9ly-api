import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProduct, saveProduct } from '../api/catalogue'
import { listTrackers } from '../api/trackers'
import type { CatalogueProduct } from '../api/types'
import { ApiError, isUnauthorized } from '../api/client'
import { Banner } from '../components/Banner'
import { ImageViewer } from '../components/ImageViewer'
import { PageHeader } from '../components/PageHeader'
import { MessageSpinner } from '../components/Spinner'
import { WatchButton } from '../components/WatchButton'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** One saved product, with the control to start or stop watching it. */
export function ProductDetail() {
  const { productId } = useParams()
  const { invalidate } = useSession()
  const { t } = useI18n()
  const [product, setProduct] = useState<CatalogueProduct | null>(null)
  const [watching, setWatching] = useState(false)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [viewing, setViewing] = useState<string | null>(null)

  const id = Number(productId)

  const load = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError(t('error.productId', { id: productId ?? '' }))
      return
    }

    setError('')
    setMissing(false)

    try {
      setProduct(await getProduct(id))

      const trackers = await listTrackers()
      setWatching(trackers.some((t2) => t2.target?.product_id === id))
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()

      // Not saved yet is the expected case this page exists to handle: offer to
      // fetch it rather than showing a dead end.
      if (caught instanceof ApiError && caught.status === 404) {
        setMissing(true)
        return
      }

      setError(apiErrorMessage(caught, t, 'error.product'))
    }
  }, [id, productId, invalidate, t])

  useEffect(() => {
    void load()
  }, [load])

  async function onFetch() {
    setFetching(true)
    setError('')

    try {
      setProduct(await saveProduct(id))
      setMissing(false)
    } catch (caught) {
      setError(apiErrorMessage(caught, t, 'error.product'))
    } finally {
      setFetching(false)
    }
  }

  if (missing) {
    return (
      <section>
        <PageHeader title={`${t('products.title')} ${id}`} />

        <Banner kind="info">{t('product.missing')}</Banner>
        {error ? <Banner kind="error">{error}</Banner> : null}

        <div className="modal-actions mt-4">
          <Link className="btn-link" to="/products">
            {t('product.backToList')}
          </Link>
          <button type="button" className="btn btn-primary" disabled={fetching} onClick={onFetch}>
            {fetching ? t('products.fetchBusy') : t('products.fetchSubmit')}
          </button>
        </div>
      </section>
    )
  }

  if (!product) {
    return error ? (
      <section>
        <Banner kind="error">{error}</Banner>
      </section>
    ) : (
      <MessageSpinner messageKey="loading.product" fields={{ id: productId ?? '' }} />
    )
  }

  return (
    <section>
      <PageHeader title={product.title ?? `${t('products.title')} ${product.product_id}`}>
        <WatchButton
          productId={product.product_id}
          watching={watching}
          onChanged={setWatching}
          onError={setError}
        />
        <Link className="btn-link" to="/products">
          {t('product.back')}
        </Link>
      </PageHeader>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {watching ? <Banner kind="info">{t('product.watchingBanner')}</Banner> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="card">
          <h3 className="mb-4">{t('product.details')}</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
            <Fact label={t('product.factId')} value={String(product.product_id)} />
            <Fact label={t('product.factPrice')} value={product.price ?? t('generic.unknown')} />
            <Fact
              label={t('product.factAvailable')}
              value={product.available ? t('generic.yes') : t('generic.no')}
            />
            <Fact
              label={t('product.factCategories')}
              value={product.categories.length ? product.categories.join(', ') : t('generic.unknown')}
            />
            <Fact label={t('product.factImages')} value={String(product.images.length)} />
            <Fact label={t('product.factFigures')} value={String(product.figures.length)} />
          </dl>
        </div>

        {product.description ? (
          <div className="card">
            <h3 className="mb-3">{t('product.description')}</h3>
            <p className="max-h-80 overflow-auto text-sm whitespace-pre-wrap text-muted">
              {product.description}
            </p>
          </div>
        ) : null}
      </div>

      {product.images.length ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {product.images.map((url, position) => (
            // A button rather than a bare image, because the thumbnail is only
            // ever a way to ask for the whole picture — the same reason a row's
            // "Open" is a link and not a decoration.
            <button
              key={url}
              type="button"
              onClick={() => setViewing(url)}
              aria-label={t('product.enlarge', { position: position + 1, total: product.images.length })}
              className="group overflow-hidden rounded-lg border border-line bg-surface transition-[border-color,transform] duration-150 hover:-translate-y-0.5 hover:border-line-strong"
            >
              <img
                src={url}
                alt=""
                loading="lazy"
                className="aspect-square w-full object-cover transition-opacity duration-200 group-hover:opacity-80"
              />
            </button>
          ))}
        </div>
      ) : null}

      {viewing ? (
        <ImageViewer
          src={viewing}
          alt={product.title ?? `${t('products.title')} ${product.product_id}`}
          onClose={() => setViewing(null)}
        />
      ) : null}
    </section>
  )
}

/** One label and its value, stacked so a two-column grid of them stays aligned. */
function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="mb-1 text-[0.6875rem] font-medium tracking-wider text-faint uppercase">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}

