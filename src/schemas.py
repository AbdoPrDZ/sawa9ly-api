"""Request and response bodies for the API."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

#: What a `Page` carries. Bound to the concrete `Out` schema by each route, so
#: `/api/v1/catalogue` is documented as a page of products rather than of
#: something untyped.
T = TypeVar("T")


class PageMeta(BaseModel):
  """How a page of results was drawn, for a list route that was asked for one.

  `limit` is null when the request asked for no limit, which is the default and
  the case the CLI and the machine contract use. `has_more` is here so a client
  does not have to work out `offset + len(items) < total` itself, which is the
  one piece of arithmetic every list screen would otherwise repeat.
  """

  total: int
  limit: int | None = None
  offset: int = 0
  has_more: bool = False


class Page(PageMeta, Generic[T]):
  """One page of a list.

  **A change to the list contract.** These routes used to answer with a bare JSON
  array; they now answer with an object whose rows are under `items`. There is no
  way to carry a total count inside an array, so this could not be done without
  changing the shape — the alternative was a header nobody would read.

  What did not change: `q`, `limit` and `offset` are all optional, and a request
  that passes none of them still gets every row. A caller that wants everything
  only has to read one more key.
  """

  items: list[T]


class ProductOut(BaseModel):
  product_id: int
  title: str
  # Named `available`, not `availability`. `availability` is what the site calls
  # it and what the scraper reads, but the column, the model and every consumer
  # — the CLI, the dashboard — use `available`. This field was declared as
  # `availability` and never matched, which went unnoticed because the list
  # routes returned a bare `list`, so FastAPI validated nothing. Typing the route
  # as `Page[ProductOut]` made the mismatch surface as a 500.
  available: bool
  images: list[str]
  description: str
  figures: list[str]
  price: str
  categories: list[str]


class CartOut(BaseModel):
  quantities: dict[int, int]
  prices: dict[int, int]
  count: int
  total: int | None


class CartStateOut(BaseModel):
  """Result of a cart mutation that reports the cart itself."""

  cart: CartOut


class ProductInCartOut(BaseModel):
  product_id: int
  in_cart: bool
  cart: CartOut | None = None


class QuantityIn(BaseModel):
  quantity: int = Field(ge=1, description="New quantity, at least 1")


class PriceIn(BaseModel):
  price: int = Field(ge=1, description="New unit price, at least 1")


class CheckoutClient(BaseModel):
  """The order form. Every field except note is required by the site."""

  full_name: str | None = None
  phone: str | None = None
  adresse: str | None = None
  wilaya_id: int | None = None
  commune_id: int | None = None
  note: str | None = None


class CheckoutIn(BaseModel):
  quantities: dict[int, int] = Field(
    default_factory=dict, description="product id to quantity"
  )
  prices: dict[int, int] = Field(
    default_factory=dict, description="product id to unit price"
  )
  client: CheckoutClient = Field(default_factory=CheckoutClient)
  dry_run: bool = False


class CheckoutOut(BaseModel):
  success: bool
  order: object | None = None
  step: int | None = None
  total: int | None = None
  errors: dict[str, list[str]] = Field(default_factory=dict)


class UserOut(BaseModel):
  username: str
  created_at: object | None = None


class ApiKeyOut(BaseModel):
  """A key. `key` is only present in the response that creates it."""

  prefix: str
  label: str | None = None
  created_at: object | None = None
  expires_at: object | None = None
  last_used_at: object | None = None
  revoked: bool = False
  key: str | None = None


# --- catalogue, clients and orders ------------------------------------


class ProductSaveIn(BaseModel):
  """No fields; the body only exists so the POST accepts JSON."""


class DeliveryPriceOut(BaseModel):
  """What it costs to deliver to one wilaya, as of the last scrape.

  Global rather than per-user, so nothing here identifies whose scrape it was.
  `price` is home delivery and `office_price` is collection from the carrier's
  office; both are null for a wilaya the site does not deliver to, which
  `available` says outright rather than leaving to be inferred from the nulls.

  `wilaya_name` is here because the shipping page prints a number and a name but
  the scraper only reads the number, so without the key the response says `16` and
  nothing about who that is. It is the site's own Arabic spelling.
  """

  id: int
  wilaya_id: int
  wilaya_name: str | None = None
  available: bool
  price: float | None = None
  office_price: float | None = None


class DeliveryPriceSyncIn(BaseModel):
  """No fields; the body only exists so the POST accepts JSON."""


class WilayaOut(BaseModel):
  """One wilaya, under the site's own id.

  `number` is the zero-padded form the site prints beside the name (`01`), which
  is what a saved recipient or an order line refers to, so both are returned.
  """

  id: int
  name: str
  number: str | None = None


class CommuneOut(BaseModel):
  """One commune, under the site's own id and naming its wilaya.

  `wilaya_id` is here rather than left implicit because the pairing is the thing
  that is not derivable from the site — a client form needs it to offer the right
  communes, and the id is what the checkout form is ultimately sent.
  """

  id: int
  wilaya_id: int
  name: str


class ClientIn(BaseModel):
  """A recipient to save.

  `wilaya_id` and `commune_id` are the site's own ids, not names — the site
  requires the numbers, and the site decides which communes belong to a wilaya.
  """

  full_name: str
  phone: str | None = None
  adresse: str | None = None
  wilaya_id: int | None = None
  commune_id: int | None = None


class ClientOut(BaseModel):
  """A saved recipient.

  **`note` was removed.** It was never read by anything, and a note belongs to an
  order or one of its lines, which both still have one. This is a change to the
  published shape: a caller reading `client.note` gets nothing rather than null.
  """

  id: int
  user_id: int
  full_name: str
  phone: str | None = None
  adresse: str | None = None
  wilaya_id: int | None = None
  commune_id: int | None = None


class OrderCreateIn(BaseModel):
  client_id: int | None = None
  note: str | None = None


class OrderLineIn(BaseModel):
  # `note` is read only by the add route. The set-quantity and set-price routes
  # share this body and ignore it, exactly as they ignore each other's field.
  product_id: int | None = None
  quantity: int = Field(default=1, ge=1)
  price: int | None = Field(default=None, ge=1)
  note: str | None = None


class OrderCheckoutIn(BaseModel):
  dry_run: bool = False


class PageCreateIn(BaseModel):
  """A new landing page. `product_id` is the sawa9ly id, as everywhere else."""

  product_id: int
  title: str = Field(min_length=1)
  html: str = ""


class PageUpdateIn(BaseModel):
  """A change to a page. Every field is optional: absent means unchanged.

  Sending `html` as an empty string clears it, which is different from omitting
  the key. Omitting the key is the only way to leave the markup alone.
  """

  title: str | None = Field(default=None, min_length=1)
  html: str | None = None
  state: str | None = None


class PageOut(BaseModel):
  id: int
  user_id: int
  # Our own products.id, the thing a line is keyed by. The sawa9ly id comes
  # back alongside it so a caller never has to guess which one it holds.
  product_id: int
  sawa9ly_product_id: int | None = None
  product_title: str | None = None
  # The token the page is served under. `id` must never appear in a public URL,
  # because it is ours and enumerable.
  public_id: str
  title: str
  html: str
  state: str
  created_at: str | None = None
  updated_at: str | None = None


class OrderOut(BaseModel):
  id: int
  state: str
  client_id: int | None = None
  # The order number the website generated when this was posted, e.g. 879988.
  # Null until then, and for a draft or a cancelled order that never reached the
  # site.
  origin_id: int | None = None
  reference: str | None = None
  note: str | None = None
  total: int
  lines: list[dict] = Field(default_factory=list)
  created_at: str | None = None
  # The owner's username. Only the super-only admin listing sets it, because it
  # is the one view that spans users and so has to say whose orders they are;
  # the per-user routes omit it, where it would be redundant.
  username: str | None = None


# --- dashboard auth and administration ---------------------------------


class LoginIn(BaseModel):
  username: str = Field(min_length=1, description="Username, not the sawa9ly email")
  password: str = Field(min_length=1)


class SessionUserOut(BaseModel):
  """Who is signed in, as the shell needs to know it.

  `locale` is here rather than only on the profile because the whole interface is
  written in it: the shell has to set the document language and direction before
  it renders anything, and it cannot wait for the profile page to load. The
  server is the authority — the same value decides the language of this user's
  Telegram notifications.
  """

  id: int
  username: str
  role: str
  is_admin: bool
  locale: str = "en"


class SessionOut(BaseModel):
  """A signed-in dashboard session.

  `token` is a signed token, not an API key. It expires, and it is only ever
  accepted on the `/api/auth` and `/api/admin` routes.
  """

  token: str
  token_type: str = "bearer"
  expires_in: int
  user: SessionUserOut


class ProfileOut(BaseModel):
  """The signed-in user's own account."""

  id: int
  username: str
  role: str
  is_admin: bool
  can_log_in: bool
  has_sawa9ly_credentials: bool
  sawa9ly_email: str | None = None
  has_sawa9ly_session: bool = False
  locale: str = "en"
  """Which language this user reads, and gets their notifications in."""


class ProfileIn(BaseModel):
  """Self-service changes to one's own account.

  Every field is optional and absent means unchanged, so the form can send only
  what was edited. `sawa9ly_password` is write-only and never returned.
  """

  sawa9ly_email: str | None = None
  sawa9ly_password: str | None = None
  password: str | None = Field(default=None, min_length=1)
  locale: str | None = Field(default=None, description="'en', 'fr' or 'ar'")


class Sawa9lyLoginOut(BaseModel):
  """The result of asking the site for a session."""

  success: bool
  username: str
  message: str
  has_session: bool = False


# --- tracking ---------------------------------------------------------


class TrackerIn(BaseModel):
  """A product to start watching."""

  product_id: int


class TrackerOut(BaseModel):
  id: int
  user_id: int
  target_model: str
  target_id: int
  created_at: str | None = None
  last_checked_at: str | None = None
  last_changed_at: str | None = None
  target: dict | None = None
  """The watched product's catalogue entry, resolved for display."""


class WatchedTrackerOut(TrackerOut):
  created: bool = False
  """False when the user was already watching it, which is not an error."""


class AdminUserOut(BaseModel):
  """A user as the dashboard sees it.

  `active_api_keys` counts only keys that are neither revoked nor expired, which
  is the number an operator actually cares about.

  A user owns their own sawa9ly and Telegram settings, so an admin sees whether
  they are set up — `has_sawa9ly_credentials` and `telegram_chat_id` — and never
  the values. That is enough to answer "why is this account not syncing?" without
  the admin holding somebody else's credentials.
  """

  id: int
  username: str
  role: str
  is_admin: bool
  """False for a `super`, which the dashboard may not change or delete. The UI
    disables the controls from this rather than guessing."""
  can_be_managed: bool = True
  has_sawa9ly_credentials: bool = False
  telegram_chat_id: str | None = None
  """Which chat this user's notifications go to, or null. Not a credential, and
    the reason a super needs it: to tell somebody which chat they linked."""
  can_log_in: bool = False
  active_api_keys: int = 0
  clients: int = 0
  orders: int = 0
  created_at: str | None = None


class AdminUserIn(BaseModel):
  """Fields the dashboard may change. Every one is optional.

  `password` is the dashboard login password and is hashed; it is never
  returned. There is deliberately no `sawa9ly_email` or `sawa9ly_password` here:
  those belong to the user, who sets them on their own profile. An administrator
  who could type them in could also sign in as that user on the site.

  A `role` of `super` is rejected by the API: the dashboard can neither hand out
  nor remove that role. See `src/services/accounts.py`.
  """

  role: str | None = Field(default=None, description="'admin' or 'user'")
  password: str | None = Field(default=None, min_length=1)


class AdminUserCreateIn(AdminUserIn):
  username: str = Field(min_length=1, max_length=64)


class AdminApiKeyOut(BaseModel):
  id: int
  user_id: int
  username: str
  prefix: str
  type: str = "api"
  """Which surface this key is accepted by: 'api' or 'mcp'."""
  label: str | None = None
  revoked: bool = False
  usable: bool = False
  created_at: object | None = None
  last_used_at: object | None = None
  expires_at: object | None = None
  key: str | None = Field(default=None, description="Only on creation")


class AdminApiKeyCreateIn(BaseModel):
  type: str = Field(default="api", description="'api' or 'mcp'")
  label: str | None = None
  expires_in_days: int | None = Field(default=None, ge=1)


# --- telegram ----------------------------------------------------------


class TelegramBindingOut(BaseModel):
  """A user's link to a Telegram chat.

  No code is ever returned. The code exists only in the URL handed out at the
  moment it is issued, so there is nothing here to redact and nothing here to
  leak later.
  """

  user_id: int
  bound: bool = False
  chat_id: str | None = None
  chat_type: str | None = None
  chat_title: str | None = None
  chat_username: str | None = None
  code_pending: bool = False
  """True while a code is outstanding and unused, so the dashboard can say
    "waiting for you to open the link" instead of showing nothing."""
  code_expires_at: str | None = None
  verified_at: str | None = None
  created_at: str | None = None


class TelegramLinkOut(BaseModel):
  """A freshly issued binding link.

  `url` and `code` are the plaintext, shown once: the code is stored only as a
  hash, so this response is the only time it can be read.
  """

  username: str
  url: str
  code: str
  expires_at: str | None = None
