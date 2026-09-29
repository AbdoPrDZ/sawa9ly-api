import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProduct, saveProduct } from '../api/catalogue'
import { listTrackers } from '../api/trackers'
import type { CatalogueProduct } from '../api/types'
import { ApiError, isUnauthorized } from '../api/client'
import { Banner } from '../components/Banner'
import { Spinner } from '../components/Spinner'
import { WatchButton } from '../components/WatchButton'
import { useSession } from '../session/useSession'

/** One saved product, with the control to start or stop watching it. */
export function ProductDetail() {
  const { productId } = useParams()
  const { invalidate } = useSession()
  const [product, setProduct] = useState<CatalogueProduct | null>(null)
  const [watching, setWatching] = useState(false)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const [fetching, setFetching] = useState(false)

  const id = Number(productId)

  const load = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setError(`'${productId}' is not a product id.`)
      return
    }

    setError('')
    setMissing(false)

    try {
      setProduct(await getProduct(id))

      const trackers = await listTrackers()
      setWatching(trackers.some((t) => t.target?.product_id === id))
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()

      // Not saved yet is the expected case this page exists to handle: offer to
      // fetch it rather than showing a dead end.
      if (caught instanceof ApiError && caught.status === 404) {
        setMissing(true)
        return
      }

      setError(caught instanceof Error ? caught.message : 'Could not load the product.')
    }
  }, [id, productId, invalidate])

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
      setError(caught instanceof Error ? caught.message : 'Could not fetch the product.')
    } finally {
      setFetching(false)
    }
  }

  if (missing) {
    return (
      <section>
        <div className="section-head">
          <h2>Product {id}</h2>
        </div>

        <Banner kind="info">
          This product is not in the catalogue. Fetching it reads its page from sawa9ly and
          stores the result.
        </Banner>

        {error ? <Banner kind="error">{error}</Banner> : null}

        <div className="modal-actions">
          <Link className="ghost link" to="/products">
            Back to products
          </Link>
          <button type="button" className="primary" disabled={fetching} onClick={onFetch}>
            {fetching ? 'Fetching…' : 'Fetch from site'}
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
      <Spinner label={`Loading product ${productId}`} />
    )
  }

  return (
    <section>
      <div className="section-head">
        <h2>{product.title ?? `Product ${product.product_id}`}</h2>
        <div className="section-actions">
          <WatchButton
            productId={product.product_id}
            watching={watching}
            onChanged={setWatching}
            onError={setError}
          />
          <Link className="ghost link" to="/products">
            Back
          </Link>
        </div>
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {watching ? (
        <Banner kind="info">
          Watching this product. The queue checks it every pass and stamps the time here, so a
          price or availability change is picked up without refreshing.
        </Banner>
      ) : null}

      <div className="cards">
        <div className="card">
          <h3>Details</h3>
          <dl className="facts">
            <dt>Product id</dt>
            <dd>{product.product_id}</dd>
            <dt>Price</dt>
            <dd>{product.price ?? '—'}</dd>
            <dt>Available</dt>
            <dd>{product.available ? 'yes' : 'no'}</dd>
            <dt>Categories</dt>
            <dd>{product.categories.length ? product.categories.join(', ') : '—'}</dd>
            <dt>Images</dt>
            <dd>{product.images.length}</dd>
            <dt>Figures</dt>
            <dd>{product.figures.length}</dd>
          </dl>
        </div>

        {product.description ? (
          <div className="card">
            <h3>Description</h3>
            <p className="description">{product.description}</p>
          </div>
        ) : null}
      </div>

      {product.images.length ? (
        <div className="gallery">
          {product.images.map((url) => (
            <img key={url} src={url} alt="" loading="lazy" />
          ))}
        </div>
      ) : null}
    </section>
  )
}
