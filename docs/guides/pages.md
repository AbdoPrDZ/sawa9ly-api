# Landing pages

A published page is served at **`/pages/{public_id}`**:

```text
http://127.0.0.1:8000/pages/7d_3zlLqxz0DZ6k2RiaKzg
```

```bash
python main.py page create 5663 "Summer offer" --html "<h1>Summer</h1>" --user alice
python main.py page list --user alice
python main.py page state 1 publish      # now it is served
```

`public_id` is 22 URL-safe characters of randomness, unique across **every**
user's pages, and unrelated to the row `id` — which is ours and enumerable, so it
must never appear in a public address. The dashboard shows the full link on the
**Pages** list and in the edit dialog, and only makes it clickable once the page
is published.

Note the two things called "pages", which are deliberately different resources
behind different credentials:

| Path | What it is |
| --- | --- |
| `/pages/{public_id}` | the **public** page, as HTML, for anyone with the link. No sign-in. |
| `/api/v1/pages`, `/api/v1/pages/{id}` | the signed-in user's **own** pages, as JSON. Dashboard token or API key. |

The public route is a catch-all registered **last**, so a request for an API
route, a dashboard route or `/docs` is matched before it ever gets there.
`/pages` with no id is a 404, and the app's own Pages page lives at
`/dashboard/pages`, so the two cannot collide.

In development, `npm run dev` proxies `/pages` to the API along with `/api`. That
matters: the link the dashboard shows is built from `window.location.origin`, so
in dev that is port 5173, and Vite would otherwise refuse it with a "public base
URL" error. With the proxy, a published page is reachable on `localhost:5173` and
on `localhost:8000` alike, so dev behaves like production. **Restart
`npm run dev` after changing `vite.config.ts`.**

A public address that serves no page answers **404 with a plain page**, not the
API's JSON: these URLs are followed by people, not clients. That covers a page
that was never published, one that has been archived, one whose token is wrong
and the bare /pages — all four look the same, so an unpublished page leaks
nothing, not even that it exists. The root / does the same and points at the
dashboard. Anything under /api still answers JSON, because that is what its
callers parse.

## The sandbox header, and why it is not decoration

The dashboard and the published pages share an origin, and the dashboard keeps
its session token in `localStorage`. So a served page is sent with:

```text
Content-Security-Policy: sandbox
X-Content-Type-Options: nosniff
Cache-Control: no-cache
```

Without `sandbox`, any script in a published page runs on that same origin and
can read that token — so a page an administrator visited would hand over their
session. `sandbox` gives the page a unique, opaque origin with no script
execution: HTML and CSS render as written, and the dashboard's origin is
unreachable from the page.

**The cost is that a page cannot run its own JavaScript.** If you need that, the
fix is to serve pages from a *different origin* — a second port or host is a real
origin boundary — not to loosen the header. Do not add `allow-scripts` while
pages and the dashboard share an origin.

**Two product ids, as everywhere.** You *create* a page by the **sawa9ly**
product id, because that is the id you have. It is stored against our own
`products.id`, and `PageOut` returns both — `product_id` (ours) and
`sawa9ly_product_id` (the site's) — so nothing downstream has to guess.

```bash
python main.py page create 5663 "Summer offer" --html "<h1>Summer</h1>" --user alice
python main.py page create 5663 "Winter offer" --user alice      # a second page, same product
python main.py page list --user alice
python main.py page list --user alice --product 5663
python main.py page list --user alice --state publish
python main.py page edit 1 --html "<h1>Summer sale</h1>"          # markup only
python main.py page state 1 publish
python main.py page show 1
```

From the dashboard: **Pages**, available to every signed-in user, lists and edits
yours and creates new ones. A product that is not in the catalogue yet is fine —
the row is created for it, the same as when you add one to an order.

**The markup is stored verbatim.** See [the sandbox header](#the-sandbox-header-and-why-it-is-not-decoration)
for how it is served and why the response is sandboxed.

## Clients and pages are yours alone

`/api/v1/clients` and `/api/v1/pages` are scoped to the caller, and there is no
admin or super-wide view of either. A `super` asking for another user's page gets
the same 404 as anyone else. The only cross-user order view in the project is
`/api/admin/orders`, which is super-only on purpose.

Neither resource has a delete. A client is corrected by saving the same name
again, and a page is corrected by editing it, but neither can be removed from the
UI — add a `DELETE` route and a control if you want that.
