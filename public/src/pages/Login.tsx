import { useState } from 'react'
import type { FormEvent } from 'react'
import { Banner } from '../components/Banner'
import { Field } from '../components/Field'
import { useSession } from '../session/useSession'

/** Username and password, exchanged for a dashboard token. */
export function Login() {
  const { signIn } = useSession()
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
      setError(caught instanceof Error ? caught.message : 'Sign in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>sawa9ly admin</h1>
        <p className="muted">Sign in to manage users and API keys.</p>

        {error ? <Banner kind="error">{error}</Banner> : null}

        <Field label="Username">
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </Field>

        <Field label="Password" hint="Your dashboard password, not the sawa9ly one.">
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>

        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}