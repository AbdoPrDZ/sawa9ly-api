import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { BASENAME } from './api/client'
import { SessionProvider } from './session/SessionProvider'
import './styles.css'

const container = document.getElementById('root')

if (!container) throw new Error('No #root element in index.html')

createRoot(container).render(
  <StrictMode>
    {/*
      The dashboard is served from its own prefix, not the site root, so the
      router has to be told where it lives. It comes from `api/client` rather
      than being written out again here, because this value, the built asset
      URLs and the paths the client requests all have to be the same string, and
      one constant is the only way to keep them that way.

      With the basename set, every route and `Link` in the app stays relative —
      `/orders` means `<basename>/orders` — so nothing below this file needs to
      know the prefix.
    */}
    <BrowserRouter basename={BASENAME}>
      <SessionProvider>
        <App />
      </SessionProvider>
    </BrowserRouter>
  </StrictMode>,
)
