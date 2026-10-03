import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { Spinner } from './components/Spinner'
import { I18nProvider } from './i18n/I18nProvider'
import { ApiKeys } from './pages/ApiKeys'
import { Clients } from './pages/Clients'
import { Login } from './pages/Login'
import { OrderDetail } from './pages/OrderDetail'
import { Orders } from './pages/Orders'
import { Pages } from './pages/Pages'
import { ProductDetail } from './pages/ProductDetail'
import { Products } from './pages/Products'
import { ProfilePage } from './pages/Profile'
import { Shipping } from './pages/Shipping'
import { Users } from './pages/Users'
import { useSession } from './session/useSession'

/** The signed-in app.
 *
 * Everybody who is signed in gets the shell, because managing their own account
 * is not an administrator's job to unlock. Every page except Users is available
 * to every user; Users is admin-only and redirects a plain user home, so a 403 is
 * never the first thing they see.
 *
 * A user's own API keys are on that list deliberately: a key is their own
 * credential, and minting one should not need an administrator standing between
 * them and it. Shipping is here for the same reason the catalogue is — it is
 * shared reference data, so it belongs to nobody and is everybody's to read.
 */
export function App() {
  const { user, loading, signOut } = useSession()

  // Outside the signed-in check, because the login screen is translated too and
  // has no user to read a language from. `user?.locale` is the account's, and it
  // is the same value that decides the language of their notifications.
  return (
    <I18nProvider accountLocale={user?.locale}>
      <AppRoutes user={user} loading={loading} onSignOut={signOut} />
    </I18nProvider>
  )
}

/** Everything that needs a language, behind the provider. */
function AppRoutes({
  user,
  loading,
  onSignOut,
}: {
  user: ReturnType<typeof useSession>['user']
  loading: boolean
  onSignOut(): void
}) {
  // Nothing is rendered until a stored token has been checked, otherwise a
  // reload would flash the login screen at a user who is still signed in.
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Checking your session" />
      </div>
    )
  }

  if (!user) return <Login />

  return (
    <AppShell user={user} onSignOut={onSignOut}>
      <Routes>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:productId" element={<ProductDetail />} />
        <Route path="/shipping" element={<Shipping />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/pages" element={<Pages />} />
        <Route path="/keys" element={<ApiKeys />} />
        <Route
          path="/users"
          element={user.is_admin ? <Users /> : <Navigate to="/profile" replace />}
        />
        <Route
          path="*"
          element={<Navigate to={user.is_admin ? '/products' : '/profile'} replace />}
        />
      </Routes>
    </AppShell>
  )
}
