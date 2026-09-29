import { useCallback, useEffect, useState } from 'react'
import { isUnauthorized } from '../api/client'
import { createClient, listClients } from '../api/clients'
import type { Client, NewClient } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { Spinner } from '../components/Spinner'
import { CreateClientModal } from '../features/clients/CreateClientModal'
import { useSession } from '../session/useSession'

/** The signed-in user's delivery recipients, the people their orders ship to.
 *
 * Every user gets this one, not only an administrator: a client belongs to the
 * account that will place the order, so managing them is self-service, the same
 * way the profile page is.
 *
 * Saving a name that already exists updates that recipient rather than adding a
 * second one, so this is also how a recipient is corrected.
 */
export function Clients() {
  const { invalidate } = useSession()
  const [clients, setClients] = useState<Client[] | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    try {
      setClients(await listClients())
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(message(caught, 'Could not load your recipients.'))
    }
  }, [invalidate])

  useEffect(() => {
    void load()
  }, [load])

  async function onCreate(input: NewClient) {
    try {
      const saved = await createClient(input)
      setAdding(false)
      setError('')
      setNotice(`Saved ${saved.full_name}.`)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not save the recipient.'))
    }
  }

  return (
    <section>
      <div className="section-head">
        <h2>Delivery recipients</h2>
        <div className="section-actions">
          <button type="button" className="primary" onClick={() => setAdding(true)}>
            Add recipient
          </button>
        </div>
      </div>

      <p className="muted">
        These are the details an order is shipped to. They are stored against your
        account, so a checkout does not have to ask for them again. Saving a name
        that is already here updates that recipient instead of adding a second one.
      </p>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!clients ? (
        <Spinner label="Loading recipients" />
      ) : clients.length === 0 ? (
        <>
          <p className="muted">None yet. Add one above.</p>
          <AdminOnly>
            <p className="muted">
              Or from the command line:{' '}
              <code>python main.py client add &quot;Full name&quot; --user &lt;name&gt;</code>.
            </p>
          </AdminOnly>
        </>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone</th>
              <th>Adresse</th>
              <th>Wilaya</th>
              <th>Commune</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td>{client.full_name}</td>
                <td>{client.phone ?? '—'}</td>
                <td>{client.adresse ?? '—'}</td>
                <td>{client.wilaya_id ?? '—'}</td>
                <td>{client.commune_id ?? '—'}</td>
                <td className="muted">{client.note ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {adding ? (
        <CreateClientModal onCancel={() => setAdding(false)} onSubmit={onCreate} />
      ) : null}
    </section>
  )
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
