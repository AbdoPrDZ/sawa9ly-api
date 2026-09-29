import { Navigate, Route, Routes } from 'react-router-dom'
import { Spinner } from './components/Spinner'
import { TopBar } from './components/TopBar'
import { ApiKeys } from './pages/ApiKeys'
import { Clients } from './pages/Clients'
import { Login } from './pages/Login'
import { OrderDetail } from './pages/OrderDetail'
import { Orders } from './pages/Orders'
import { Pages } from './pages/Pages'
import { ProductDetail } from './pages/ProductDetail'
import { Products } from './pages/Products'
import { ProfilePage } from './pages/Profile'
import { Users } from './pages/Users'
import { useSession } from './session/useSession'

/** The signed-in app.
 *
 * Everybody who is signed in gets the shell, because managing their own account
 * is not an administrator's job to unlock. The admin pages are hidden from a
 * plain user and redirect them home, so a 403 is never the first thing they see.
 */
export function App() {
  const { user, loading, signOut } = useSession()

  // Nothing is rendered until a stored token has been checked, otherwise a
  // reload would flash the login screen at a user who is still signed in.
  if (loading) {
    return (
      <div className="login-page">
        <Spinner label="Checking your session" />
      </div>
    )
  }

  if (!user) return <Login />

  return (
    <div className="app">
      <TopBar user={user} onSignOut={signOut} />

      <main>
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:orderId" element={<OrderDetail />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/pages" element={<Pages />} />
          <Route
            path="/users"
            element={user.is_admin ? <Users /> : <Navigate to="/profile" replace />}
          />
          <Route
            path="/keys"
            element={user.is_admin ? <ApiKeys /> : <Navigate to="/profile" replace />}
          />
          <Route
            path="*"
            element={<Navigate to={user.is_admin ? '/products' : '/profile'} replace />}
          />
        </Routes>
      </main>
    </div>
  )
}
