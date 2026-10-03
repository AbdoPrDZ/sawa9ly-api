# The route table

The **machine-facing** routes sit under **`/api/v1`**:

| Route | Description |
| --- | --- |
| `GET /api/v1/products/{id}` | Scrape a product page |
| `POST /api/v1/products/{id}/cart` | Add to cart |
| `DELETE /api/v1/products/{id}/cart` | Remove from cart |
| `GET /api/v1/cart` | The cart |
| `PUT /api/v1/cart/items/{id}/quantity` | Set a quantity |
| `PUT /api/v1/cart/items/{id}/price` | Set a unit price |
| `DELETE /api/v1/cart/items/{id}` | Remove a line |
| `POST /api/v1/checkout` | Set quantities/prices, fill the form, submit |
| `GET /api/v1/catalogue`, `GET /api/v1/catalogue/{id}`, `POST /api/v1/catalogue/{id}` | Saved product info |
| `GET/POST /api/v1/clients`, `GET /api/v1/clients/{id}` | Delivery recipients |
| `GET /api/v1/shipping`, `POST /api/v1/shipping` | Delivery prices per wilaya; the POST scrapes |
| `GET /api/v1/shipping/wilayas`, `GET /api/v1/shipping/communes` | The 58 wilayas, and their communes |
| `GET/POST /api/v1/pages`, `GET/PATCH /api/v1/pages/{id}` | Landing pages, one per user |
| `GET/POST /api/v1/orders`, `GET /api/v1/orders/{id}` | Orders |
| `POST /api/v1/orders/{id}/lines` | Add a product to a draft |
| `PUT/DELETE /api/v1/orders/{id}/lines/{product}` | Edit or remove a line |
| `POST /api/v1/orders/{id}/checkout` | Submit a draft order |
| `GET/POST /api/v1/trackers`, `DELETE /api/v1/trackers` | Watched products for change tracking |

The prefix is the version of the **wire format**, not of the application, and the
two move independently — a bug fix can ship as 1.3.1 while the contract is still
`/api/v1`. A future `/v2` is added alongside `/api/v1`, never in place of it.

**Three groups are deliberately unversioned**, because nothing outside this
project consumes them:

| Route | Description | Why no version |
| --- | --- | --- |
| `GET /api/health` | Liveness, no auth | A load balancer or container health check is configured against a fixed path; versioning it breaks those silently |
| `GET /api/me` | The user the key belongs to | Meta route, not part of the resource contract |
| `/api/auth/*`, `/api/admin/*` | The dashboard's own API | The dashboard in `dashboard/` is the only caller, so there is no second consumer to keep compatible |

The admin routes need `Authorization: Bearer <token>` from `POST /api/auth/login`
with an admin's username and password:

| Route | Description |
| --- | --- |
| `POST /api/auth/login` | Exchange username + password for a token (12h) |
| `GET /api/auth/me` | The signed-in user |
| `GET/PATCH /api/auth/me/profile` | Your own profile, any role |
| `POST /api/auth/me/sawa9ly-login` | Refresh your sawa9ly session |
| `GET/POST /api/admin/users` | List or create users |
| `PATCH/DELETE /api/admin/users/{id}` | Edit or delete a user |
| `GET /api/admin/api-keys` | Every key, every user |
| `POST /api/admin/users/{id}/api-keys` | Issue a key; plaintext in the response only |
| `DELETE /api/admin/api-keys/{id}` | Revoke a key |
| `GET /api/admin/orders` | **Super only.** Every user's orders, not filtered by user |
| `GET /api/admin/orders/{id}` | **Super only.** One order, whoever owns it |

A valid token for a non-admin gets 403, not 401, so a client can tell "sign in"
from "not allowed". `/api/admin/orders` asks for the `super` role specifically, so an
`admin` gets 403 there too — it is the one route that crosses user boundaries.
