# API Guide

How to call the sawa9ly HTTP API. The machine-readable reference — every route,
with request and response schemas — is the OpenAPI document the server serves at
`/docs`; this guide covers the things `/docs` cannot tell you: which credential a
route wants, what its errors mean, and how the pieces fit into a workflow.

## Contents

- [Getting a credential](#getting-a-credential)
- [The two credentials](#the-two-credentials)
- [Versioning](#versioning)
- [Conventions](#conventions)
- [Errors](#errors)
- [Workflows](#workflows)
- [Placing an order](#placing-an-order)
- [Etiquette](#etiquette)

## Getting a credential

Machine callers use an API key. Create one against a user:

```bash
python main.py apikey create --user alice --label "my integration"
```

The plaintext key is printed **once** and never again — only its hash is stored.
If you lose it, create another. It looks like `sk_…`, and you can revoke it by
its short prefix:

```bash
python main.py apikey revoke --user alice <prefix>
```

An API key acts *as* its user. It is not a scoped token: it carries that user's
whole identity, including their sawa9ly session and therefore their cart.

## The two credentials

| | API key | Dashboard token |
| --- | --- | --- |
| Presented as | `X-API-Key: sk_…` or `Authorization: Bearer sk_…` | `Authorization: Bearer eyJ…` |
| Who holds it | your integration | a person, in a browser |
| Names a user | yes, permanently | yes, until it expires |
| Expires | only if you gave `--expires-in-days`, otherwise never | 12 hours |
| Used on | `/api/v1/*` | `/api/auth/*`, `/api/admin/*` |

`Authorization: Bearer` is overloaded on purpose to keep machine callers
conventional, but the two token types are not interchangeable: an API key on an
`/api/admin` route is not a dashboard token and will not work.

Get a dashboard token by exchanging credentials:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"admin","password":"..."}'
```

The `/api/auth` and `/api/admin` routes exist for the bundled dashboard. If you are
writing an integration, you want an API key and `/api/v1`.

## Namespacing and versioning

**Every route sits under `/api`.** That outer namespace is where the whole
surface lives, so the whole surface can be mounted somewhere else later without
any of its paths changing. The dashboard's own assets are the one exception and
are served from `/dashboard`, and a published landing page is served from
`/pages/{public_id}` — both outside `/api`, because they are HTML for a person
rather than a resource for a client.

The machine-facing routes are then versioned: **`/api/v1`**. That prefix is the
version of the wire format, not of the application — the two move independently,
so a bug fix can ship as 1.3.1 while the contract is still `/api/v1`. A future
`/v2` will be added *alongside* `/api/v1`, never in place of it, so existing clients
keep working.

Three things are unversioned, each for a different reason:

| Route | Why |
| --- | --- |
| `GET /api/health` | A load balancer or container health check is configured against a fixed path. |
| `GET /api/me` | A meta route, not part of the resource contract. |
| `/api/auth/*`, `/api/admin/*` | The bundled dashboard is the only caller. |

## Conventions

- Request and response bodies are JSON. Send `content-type: application/json`.
- Credentials go in a header, never a query string — a query string ends up in
  proxy logs and browser history.
- `GET /api/v1/catalogue/{id}` and friends return the resource. Creation returns
  `201` with the created object.
- A dashboard token is verified against the server on every request, so revoking
  a key or demoting a user takes effect immediately rather than at expiry.

## Errors

Every error body is `{"detail": "..."}` with a human-readable message that says
what to do next. Validation failures are the one exception: FastAPI returns `422`
with `detail` as a *list* of `{loc, msg, type}`, so handle both shapes.

| Code | Meaning |
| --- | --- |
| `400` | The request was understood but the values are not acceptable. |
| `401` | No credential, or an unknown/revoked/expired one. `detail` says which. |
| `403` | Valid credential, not allowed to do this. Deliberately distinct from `401` so a client can tell "sign in" from "not allowed". |
| `404` | No such resource. |
| `409` | **You asked for something impossible** — a price below the site's minimum, a quantity it will not accept, a conflicting change. |
| `422` | Body failed validation; `detail` is a list. |
| `502` | **The site broke.** sawa9ly.app rejected or dropped the call, or sent something unparseable. This is not your fault and is usually worth retrying later. |

The `409` / `502` split is the one worth internalising: `409` means fix your
request, `502` means the upstream site is unhappy. Treat them differently.

> **Note.** `/api/v1/catalogue` currently answers **without any credential**. Every
> other `/api/v1` route needs an API key. If you are calling it, do not send secrets
> expecting them to be checked.

## Workflows

### Save a product to the catalogue

```bash
curl -X POST http://127.0.0.1:8000/v1/catalogue/5663 -H "X-API-Key: sk_..."
```

This scrapes the live product page and stores the result. It returns the saved
product. From then on, read it with `GET /api/v1/catalogue/5663` rather than
re-scraping.

### Build and inspect a cart

```bash
curl -X POST   http://127.0.0.1:8000/v1/products/5663/cart   -H "X-API-Key: sk_..."
curl -X PUT    http://127.0.0.1:8000/v1/cart/items/5663/quantity -H "X-API-Key: sk_..." -H 'content-type: application/json' -d '{"quantity":2}'
curl -X PUT    http://127.0.0.1:8000/v1/cart/items/5663/price     -H "X-API-Key: sk_..." -H 'content-type: application/json' -d '{"price":2500}'
curl           http://127.0.0.1:8000/v1/cart                   -H "X-API-Key: sk_..."
```

Two things bite here, and they are properties of the site rather than of this
API:

- **Quantities are server-side.** The `wire:model` binding on the quantity input
  only mutates a client-side snapshot; it neither recomputes the total nor
  survives a reload. The server's cart only changes through the increment and
  decrement actions, so this endpoint steps one unit per request, and refuses a
  jump larger than 50.
- **Prices are not server-side.** They live in the component state, are reflected
  in the total for the request that set them, and are carried into checkout from
  there. They do **not** survive a page reload.

So a price you set is not durable — anything that re-reads the cart page can lose
it. That is why checkout re-applies prices immediately before submitting.

## Placing an order

**Read this before calling checkout.** An order submitted to sawa9ly.app cannot
be cancelled from here. There is no undo endpoint, because there is no undo at
the site.

`POST /api/v1/checkout` takes the quantities, the prices, and the delivery details,
and submits the order. Use `dry_run` to stop before the form:

```json
{
  "quantities": {"5663": 2},
  "prices": {"5663": 2500},
  "client": {
    "full_name": "...",
    "phone": "...",
    "adresse": "...",
    "wilaya_id": 16,
    "commune_id": 1001,
    "note": "anything optional"
  },
  "dry_run": true
}
```

With `dry_run: true` the cart is staged and the call returns where it stopped,
without submitting. The response is
`{success, order, step, total, errors}`; `step` tells you how far it got and
`errors` carries the site's own field-level complaints.

**Every client field is required for a real submit.** Omit one and the site
rejects it — which is a safe way to test the call without placing an order. The
response also tells you when `next_step` refused to advance, which usually means
the prices leave the order's commission below the site's 5% minimum.

`wilaya_id` must be sent before `commune_id`, because it drives the list of
commune options; the endpoint handles that ordering for you.

### Draft orders

For anything you want to review before submitting, use the order resource rather
than `/api/v1/checkout`. Build a draft, add lines, then submit it explicitly:

```bash
curl -X POST http://127.0.0.1:8000/v1/orders -H "X-API-Key: sk_..." -H 'content-type: application/json' -d '{"client_id":1}'
curl -X POST http://127.0.0.1:8000/v1/orders/1/lines -H "X-API-Key: sk_..." -H 'content-type: application/json' -d '{"product_id":5663,"quantity":2,"price":2500}'
curl -X POST http://127.0.0.1:8000/v1/orders/1/checkout -H "X-API-Key: sk_..."
```

A line is addressed by **product** id, not line id, because a product appears at
most once in an order. Drafts live in the local database, so nothing is sent to
the site until the final call.

## Etiquette

Every `/api/v1` call that touches the site's cart reaches out to sawa9ly.app, which
has no API and does not expect programmatic traffic. A few things keep this a good
guest:

- **Do not poll the cart in a tight loop.** Each read is a real page request.
- **Prefer the catalogue over re-scraping.** `GET /api/v1/catalogue/{id}` is a local
  read; `POST /api/v1/catalogue/{id}` is a live scrape.
- **Quantity changes cost one request per unit**, and the endpoint caps a single
  jump at 50 units. Do not attempt to move thousands.
- **There is deliberately no endpoint that triggers a tracking pass.** One web
  request fanning out into hundreds of requests to the site is the fastest way to
  be blocked. The queue runs on its own schedule (`CRON_INTERVAL`, default 300s)
  and paces itself with `CRON_DELAY` (default 1.0s per product).

## See also

- `python main.py router` — the whole route table, one row per method
- `python main.py --json router` — the same, as JSON
- `/docs` — the live OpenAPI reference for schemas
- [README.md](README.md) — installation, configuration, and the CLI
