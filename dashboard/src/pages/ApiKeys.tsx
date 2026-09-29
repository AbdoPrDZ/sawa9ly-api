import { useCallback, useEffect, useMemo, useState } from 'react'
import { isUnauthorized } from '../api/client'
import { createKey, listKeys, revokeKey } from '../api/keys'
import type { AdminApiKey, AdminUser } from '../api/types'
import { listUsers } from '../api/users'
import { Banner } from '../components/Banner'
import { KeyState } from '../components/KeyState'
import { Spinner } from '../components/Spinner'
import { IssueKeyModal } from '../features/keys/IssueKeyModal'
import { RevealKeyModal } from '../features/keys/RevealKeyModal'
import { RevokeKeyModal } from '../features/keys/RevokeKeyModal'
import { useSession } from '../session/useSession'

export function ApiKeys() {
  const { invalidate } = useSession()
  const [keys, setKeys] = useState<AdminApiKey[] | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [issuing, setIssuing] = useState(false)
  const [revoking, setRevoking] = useState<AdminApiKey | null>(null)
  const [onlyLive, setOnlyLive] = useState(false)
  const [fresh, setFresh] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setKeys(await listKeys())
    } catch (caught) {
      if (isUnauthorized(caught)) return invalidate()
      setError(message(caught, 'Could not load API keys.'))
    }
  }, [invalidate])

  useEffect(() => {
    load()
    // The user list is only needed to populate the issue form, so a failure
    // here is not worth a message of its own.
    listUsers().then(setUsers).catch(() => setUsers([]))
  }, [load])

  const shown = useMemo(
    () => (keys ?? []).filter((key) => (onlyLive ? key.usable : true)),
    [keys, onlyLive],
  )

  async function onIssue(input: { userId: number; label: string; days?: number }) {
    try {
      const created = await createKey(input.userId, input.label, input.days)
      setIssuing(false)
      // The plaintext exists only in this response, so it is shown once and
      // then dropped; it cannot be fetched again.
      setFresh(created.key ?? null)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not issue the key.'))
    }
  }

  async function onRevoke(target: AdminApiKey) {
    try {
      await revokeKey(target.id)
      setNotice(`Key ${target.prefix}… revoked.`)
      setRevoking(null)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not revoke the key.'))
      setRevoking(null)
    }
  }

  return (
    <section>
      <div className="section-head">
        <h2>API keys</h2>
        <div className="section-actions">
          <label className="check">
            <input
              type="checkbox"
              checked={onlyLive}
              onChange={(event) => setOnlyLive(event.target.checked)}
            />
            usable only
          </label>
          <button
            type="button"
            className="primary"
            disabled={users.length === 0}
            title={users.length === 0 ? 'Create a user first' : undefined}
            onClick={() => setIssuing(true)}
          >
            Issue key
          </button>
        </div>
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      {!keys ? (
        <Spinner label="Loading keys" />
      ) : (
        <table>
          <thead>
            <tr>
              <th>Prefix</th>
              <th>Label</th>
              <th>User</th>
              <th>State</th>
              <th>Last used</th>
              <th>Expires</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {shown.map((key) => (
              <tr key={key.id}>
                <td>
                  <code>{key.prefix}…</code>
                </td>
                <td>{key.label ?? '—'}</td>
                <td>{key.username ?? `#${key.user_id}`}</td>
                <td>
                  <KeyState revoked={key.revoked} usable={key.usable} />
                </td>
                <td>{key.last_used_at ?? 'never'}</td>
                <td>{key.expires_at ?? 'never'}</td>
                <td className="row-actions">
                  <button
                    type="button"
                    className="danger"
                    disabled={key.revoked}
                    onClick={() => setRevoking(key)}
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
            {shown.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  No keys.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      )}

      {issuing ? (
        <IssueKeyModal
          users={users}
          onCancel={() => setIssuing(false)}
          onSubmit={onIssue}
        />
      ) : null}

      {revoking ? (
        <RevokeKeyModal
          apiKey={revoking}
          onCancel={() => setRevoking(null)}
          onConfirm={() => onRevoke(revoking)}
        />
      ) : null}

      {fresh ? <RevealKeyModal secret={fresh} onClose={() => setFresh(null)} /> : null}
    </section>
  )
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
