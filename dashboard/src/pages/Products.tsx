import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProducts } from '../api/catalogue'
import { listTrackers } from '../api/trackers'
import type { CatalogueProduct } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { FetchProduct } from '../components/FetchProduct'
import { Spinner } from '../components/Spinner'
import { WatchButton } from '../components/WatchButton'

/** The saved catalogue, with a way to fetch a product by its id. */
export function Products() {
  const [products, setProducts] = useState<CatalogueProduct[] | null>(null)
  const [watching, setWatching] = useState<Set<number>>(new Set())
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    try {
      setProducts(await listProducts())
    } catch (caught) {
      setError(message(caught, 'Could not load the catalogue.'))
    }
  }, [])

  // The watch state is per user, so it is read once here rather than asked for
  // on every row.
  useEffect(() => {
    void load()

    listTrackers()
      .then((trackers) =>
        setWatching(new Set(trackers.map((t) => t.target?.product_id).filter(isNumber))),
      )
      .catch(() => setWatching(new Set()))
  }, [load])

  function onWatched(productId: number, now: boolean) {
    setWatching((current) => {
      const next = new Set(current)
      if (now) next.add(productId)
      else next.delete(productId)
      return next
    })

    setNotice(now ? `Watching product ${productId}.` : `Stopped watching ${productId}.`)
  }

  function onFetched(product: CatalogueProduct) {
    setNotice(`Fetched product ${product.product_id}.`)
    setError('')
    void load()
  }

  return (
    <section>
      <div className="section-head">
        <h2>Products</h2>
      </div>

      <div className="fetch-row">
        <FetchProduct onFetched={onFetched} onError={setError} />
        <p className="muted">
          Fetches a product page from sawa9ly and stores it here. Only products you have
          fetched appear below.
        </p>
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!products ? (
        <Spinner label="Loading products" />
      ) : products.length === 0 ? (
        <>
          <p className="muted">Nothing saved yet. Fetch a product by its id above.</p>
          <AdminOnly>
            <p className="muted">
              Or run <code>python main.py catalogue save &lt;id&gt; --user &lt;name&gt;</code>.
            </p>
          </AdminOnly>
        </>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Id</th>
              <th>Title</th>
              <th>Price</th>
              <th>Available</th>
              <th>Images</th>
              <th>Watch</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.product_id}>
                <td>{product.product_id}</td>
                <td>{product.title ?? '—'}</td>
                <td>{product.price ?? '—'}</td>
                <td>{product.available ? 'yes' : 'no'}</td>
                <td className="muted">{product.images.length}</td>
                <td>
                  <WatchButton
                    productId={product.product_id}
                    watching={watching.has(product.product_id)}
                    onChanged={(now) => onWatched(product.product_id, now)}
                    onError={setError}
                    size="small"
                  />
                </td>
                <td className="row-actions">
                  <Link className="ghost link" to={`/products/${product.product_id}`}>
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function isNumber(value: number | undefined): value is number {
  return typeof value === 'number'
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
