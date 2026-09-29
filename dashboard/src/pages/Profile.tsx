import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { getProfile, sawa9lyLogin, updateProfile } from '../api/profile'
import type { Profile } from '../api/types'
import { Banner } from '../components/Banner'
import { Field } from '../components/Field'
import { RoleBadge } from '../components/RoleBadge'
import { Spinner } from '../components/Spinner'
import { TelegramCard } from '../features/telegram/TelegramCard'

/** A user's own account.
 *
 * Available to every signed-in user, whatever their role: changing your own
 * password, your own sawa9ly credentials or your own Telegram chat should never
 * need an administrator. Nobody can set these for you, which is why they are all
 * on this page and none of them are on anyone else's.
 */
export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)

  const [email, setEmail] = useState('')
  const [sawa9lyPassword, setSawa9lyPassword] = useState('')
  const [dashboardPassword, setDashboardPassword] = useState('')

  const load = useCallback(async () => {
    try {
      const loaded = await getProfile()
      setProfile(loaded)
      setEmail(loaded.sawa9ly_email ?? '')
    } catch (caught) {
      setError(message(caught, 'Could not load your profile.'))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (!profile) return <Spinner label="Loading your profile" />

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)

    // Only the fields that were actually filled in. An empty box means
    // "leave it alone"; clearing a credential is done explicitly below.
    const input: Parameters<typeof updateProfile>[0] = {}

    if (email !== (profile?.sawa9ly_email ?? '')) input.sawa9ly_email = email
    if (sawa9lyPassword) input.sawa9ly_password = sawa9lyPassword
    if (dashboardPassword) input.password = dashboardPassword

    if (Object.keys(input).length === 0) {
      setNotice('Nothing to save.')
      setBusy(false)
      return
    }

    try {
      const updated = await updateProfile(input)
      setProfile(updated)
      setEmail(updated.sawa9ly_email ?? '')
      setSawa9lyPassword('')
      setDashboardPassword('')
      setNotice('Saved.')
    } catch (caught) {
      setError(message(caught, 'Could not save your profile.'))
    } finally {
      setBusy(false)
    }
  }

  async function onSawa9lyLogin() {
    setError('')
    setNotice('')
    setLoggingIn(true)

    try {
      const result = await sawa9lyLogin()
      setNotice(result.message)
      await load()
    } catch (caught) {
      setError(message(caught, 'Could not log in to sawa9ly.'))
    } finally {
      setLoggingIn(false)
    }
  }

  return (
    <section>
      <div className="section-head">
        <h2>My profile</h2>
        <RoleBadge role={profile.role} />
      </div>

      {error ? <Banner kind="error">{error}</Banner> : null}
      {notice ? <Banner kind="success">{notice}</Banner> : null}

      <div className="cards">
        <div className="card">
          <h3>Sawa9ly account</h3>
          <p className="muted">
            {profile.has_sawa9ly_credentials
              ? 'Credentials are stored, so this account can place orders.'
              : 'Add these to let this account place orders. Nobody else can set them for you.'}
          </p>
          <p>
            Site session:{' '}
            {profile.has_sawa9ly_session ? (
              <span className="badge badge-active">ready</span>
            ) : (
              <span className="badge badge-expired">none</span>
            )}
          </p>
          <button
            type="button"
            className="primary"
            disabled={loggingIn || !profile.has_sawa9ly_credentials}
            title={
              profile.has_sawa9ly_credentials
                ? undefined
                : 'Add your sawa9ly email and password first'
            }
            onClick={onSawa9lyLogin}
          >
            {loggingIn ? 'Logging in…' : 'Log in to sawa9ly'}
          </button>
        </div>

        <form className="card" onSubmit={save}>
          <h3>Change your details</h3>

          <Field
            label="Sawa9ly email"
            hint="Leave empty to keep the current one."
          >
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="off"
            />
          </Field>

          <Field
            label="Sawa9ly password"
            hint="Leave empty to keep the current one."
          >
            <input
              type="password"
              value={sawa9lyPassword}
              onChange={(event) => setSawa9lyPassword(event.target.value)}
              autoComplete="new-password"
            />
          </Field>

          <Field
            label="Dashboard password"
            hint="How you sign in here. Leave empty to keep the current one."
          >
            <input
              type="password"
              value={dashboardPassword}
              onChange={(event) => setDashboardPassword(event.target.value)}
              autoComplete="new-password"
            />
          </Field>

          <div className="modal-actions">
            <button type="submit" className="primary" disabled={busy}>
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>

        <TelegramCard />
      </div>
    </section>
  )
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}
