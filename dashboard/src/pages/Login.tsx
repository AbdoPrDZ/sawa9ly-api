import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, BASENAME } from '../api/client'
import { Banner } from '../components/Banner'
import { Field } from '../components/Field'
import { useI18n } from '../i18n/useI18n'
import { useSession } from '../session/useSession'

/** Username and password, exchanged for a dashboard token.
 *
 * A single card, centred, because there is exactly one thing to do here and
 * nothing to navigate to until it is done. The logo is served from the
 * dashboard's own prefix, so the path is built from `BASENAME` like everywhere
 * else.
 */
export function Login() {
  const { signIn } = useSession()
  const { t } = useI18n()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)

    try {
      await signIn(username, password)
    } catch (caught) {
      // A rejected login is always a 401, and the server says the same thing for
      // a wrong username as for a wrong password on purpose. That sentence is
      // rebuilt here rather than shown from the server, so it arrives in the
      // reader's language without giving anything away.
      setError(caught instanceof ApiError && caught.status === 401 ? t('login.wrong') : t('login.failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <form className="card w-full max-w-sm animate-fade-up p-6" onSubmit={onSubmit}>
        <div className="mb-6">
          <img
            src={`${BASENAME}/logo.png`}
            alt=""
            width={28}
            height={28}
            className="mb-4 h-7 w-auto rounded object-contain"
          />
          <h1 className="mb-1">{t('login.title')}</h1>
          <p className="text-sm text-muted">{t('login.subtitle')}</p>
        </div>

        {error ? <Banner kind="error">{error}</Banner> : null}

        <Field label={t('login.username')}>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </Field>

        <Field label={t('login.password')} hint={t('login.passwordHint')}>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>

        <button type="submit" className="btn btn-primary mt-1 w-full" disabled={busy}>
          {busy ? t('login.busy') : t('login.submit')}
        </button>
      </form>
    </div>
  )
}
