import { useState } from 'react'
import { createClient, listClients } from '../api/clients'
import type { Client, NewClient } from '../api/types'
import { AdminOnly } from '../components/AdminOnly'
import { Banner } from '../components/Banner'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import { SearchInput } from '../components/SearchInput'
import { MessageSpinner } from '../components/Spinner'
import { TablePanel } from '../components/TablePanel'
import { CreateClientModal } from '../features/clients/CreateClientModal'
import { PAGE_SIZE, usePagedList } from '../hooks/usePagedList'
import { apiErrorMessage } from '../i18n/apiError'
import { useI18n } from '../i18n/useI18n'
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
  const { t } = useI18n()
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState(false)

  const list = usePagedList<Client>(listClients, {
    errorKey: 'error.recipients',
    onUnauthorized: invalidate,
  })
  const clients = list.items

  async function onCreate(input: NewClient) {
    try {
      const saved = await createClient(input)
      setAdding(false)
      list.setError('')
      setNotice(t('clients.saved', { name: saved.full_name }))
      list.reload()
    } catch (caught) {
      list.setError(apiErrorMessage(caught, t, 'error.recipients'))
    }
  }

  return (
    <section>
      <PageHeader title={t('clients.title')}>
        <button type="button" className="btn btn-primary" onClick={() => setAdding(true)}>
          {t('clients.add')}
        </button>
      </PageHeader>

      <p className="mb-5 max-w-prose text-sm text-muted">{t('clients.intro')}</p>

{list.error ? <Banner kind="error">{list.error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="mb-4 max-w-sm">
        <SearchInput
          value={list.query.term}
          onChange={list.query.setTerm}
          placeholder={t('list.searchBy', { resource: t('resource.clients') })}
          label={t('list.search')}
          busy={list.busy}
        />
      </div>

      {!clients ? (
        <MessageSpinner messageKey="loading.recipients" />
      ) : clients.length === 0 ? (
        <EmptyState>
          <p>{list.query.q ? t('clients.emptySearch') : t('clients.empty')}</p>
          <AdminOnly>
            <p className="mt-2">
              {t('clients.emptyCli')}{' '}
              <code>python main.py client add &quot;Full name&quot; --user &lt;name&gt;</code>
            </p>
          </AdminOnly>
        </EmptyState>
      ) : (
        <TablePanel>
          <thead>
            <tr>
              <th>{t('clients.col.name')}</th>
              <th>{t('clients.col.phone')}</th>
              <th>{t('clients.col.adresse')}</th>
              <th>{t('clients.col.wilaya')}</th>
<th>{t('clients.col.commune')}</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td className="font-medium">{client.full_name}</td>
                <td className="font-mono text-xs">{client.phone ?? t('generic.unknown')}</td>
                <td>{client.adresse ?? t('generic.unknown')}</td>
                <td className="text-muted">{client.wilaya_id ?? t('generic.unknown')}</td>
<td className="text-muted">{client.commune_id ?? t('generic.unknown')}</td>
              </tr>
            ))}
</tbody>
        </TablePanel>
      )}

      {clients && clients.length > 0 && (
        <Pager
          total={list.total}
          page={list.query.page}
          pageSize={PAGE_SIZE}
          hasMore={list.hasMore}
          onPage={list.query.setPage}
        />
      )}

      {adding ? (
        <CreateClientModal onCancel={() => setAdding(false)} onSubmit={onCreate} />
      ) : null}
    </section>
  )
}

