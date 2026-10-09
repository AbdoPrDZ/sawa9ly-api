"""HTML for the public storefront.

Server-rendered, with no JavaScript, because these pages share an origin with the
dashboard and the dashboard keeps its login token in `localStorage`. The
controller sends `Content-Security-Policy: sandbox allow-forms`, which gives each
page an opaque origin and no script, while still letting the checkout form POST.
The one thing that buys is the ability to render a form at all; everything
interactive is a plain link or a full-page form.

Every value that comes from a user or the site — a store name, a product title, a
commune — is escaped here. This module is the only place storefront markup is
built, so there is one place to be sure of that.

**The checkout form has no price and no quantity.** It sells one unit at the
product's sell price, which the server reads, not the form: a page a visitor can
edit must never be what decides what an order costs.
"""

from html import escape

from src import theme

#: How many stores or products to a page.
PAGE_SIZE = 24


class StorefrontPages:
  """The storefront's HTML, one method per page."""

  @staticmethod
  def _esc(value):
    """Escape text for HTML. None becomes an empty string."""
    return escape("" if value is None else str(value), quote=True)

  @staticmethod
  def _attr(value):
    """Escape a value going into an attribute, including its quotes."""
    return escape("" if value is None else str(value), quote=True)

  # --- pieces ---------------------------------------------------------

  @staticmethod
  def _styles():
    return f"""
      :root {{
        --canvas: {theme.CANVAS};
        --surface: #14181d;
        --line: #232a31;
        --ink: {theme.INK};
        --muted: {theme.MUTED};
        --accent: {theme.ACCENT};
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--canvas);
        color: var(--ink);
        font: 16px/1.6 system-ui, sans-serif;
      }}
      a {{ color: var(--accent); text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      header.top {{
        border-bottom: 1px solid var(--line);
        padding: 1rem;
      }}
      header.top a {{ color: var(--ink); font-weight: 600; }}
      main {{ max-width: 1100px; margin: 0 auto; padding: 1.5rem 1rem 4rem; }}
      h1 {{ font-size: 1.6rem; margin: 0 0 0.25rem; }}
      h2 {{ font-size: 1.1rem; margin: 2rem 0 1rem; }}
      p.lead {{ color: var(--muted); margin: 0 0 1rem; }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 1rem;
      }}
      .store-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 1rem;
      }}
      .card {{
        color: var(--ink);
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--surface);
        overflow: hidden;
      }}
      a.card {{ text-decoration: none; color: var(--ink); }}
      a.card:hover {{ text-decoration: none; border-color: var(--line-strong); }}
      .card .body {{ padding: 0.75rem; }}
      .card img.cover {{
        width: 100%;
        aspect-ratio: 1 / 1;
        object-fit: cover;
        display: block;
        background: #0e1114;
      }}
      .card div.cover {{ width: 100%; aspect-ratio: 1 / 1; background: #0e1114; }}
      .card .title {{ color: var(--ink); font-weight: 600; margin: 0 0 0.35rem; }}
      .price {{ color: var(--accent); font-weight: 700; }}
      .muted {{ color: var(--muted); }}
      .store-card {{
        display: flex;
        align-items: center;
        gap: 0.85rem;
        padding: 1rem;
      }}
      .store-card .logo {{
        width: 56px; height: 56px; border-radius: 12px;
        object-fit: cover; background: #0e1114; flex: 0 0 auto;
      }}
      .store-card .initial {{
        width: 56px; height: 56px; border-radius: 12px;
        display: grid; place-items: center;
        background: var(--accent); color: #111; font-weight: 800; font-size: 1.4rem;
        flex: 0 0 auto;
      }}
      .store-card .name {{ display: block; color: var(--ink); font-weight: 600; }}
      .store-card .meta {{ display: block; color: var(--muted); font-size: 0.8rem; margin-top: 0.15rem; }}
      form.search {{ display: flex; gap: 0.5rem; margin: 0 0 1.5rem; max-width: 380px; }}
      input, select, textarea, button {{
        font: inherit; color: var(--ink);
        background: #0e1114; border: 1px solid var(--line);
        border-radius: 8px; padding: 0.55rem 0.7rem; width: 100%;
      }}
      button {{
        cursor: pointer; background: var(--accent); color: #111;
        border-color: var(--accent); font-weight: 700; width: auto;
      }}
      .product {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
      @media (min-width: 800px) {{ .product {{ grid-template-columns: 1.1fr 1fr; }} }}
      .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 0.6rem; }}
      .gallery img {{ width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); }}
      .badge {{ display: inline-block; font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 999px; margin-inline-start: 0.5rem; }}
      .in {{ background: #16351f; color: #7fe0a0; }}
      .out {{ background: #3a1c1c; color: #f09393; }}
      fieldset {{ border: 1px solid var(--line); border-radius: 12px; padding: 1rem; margin: 0; }}
      legend {{ padding: 0 0.4rem; color: var(--muted); }}
      label.field {{ display: block; margin-bottom: 0.8rem; }}
      label.field span {{ display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.3rem; }}
      .error {{ color: #f09393; font-size: 0.8rem; margin-top: 0.25rem; }}
      .banner {{ border: 1px solid var(--line); border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 1rem; }}
      .banner.error {{ border-color: #5a2a2a; color: #f09393; }}
      .banner.ok {{ border-color: #235a35; color: #7fe0a0; }}
      .pager {{ display: flex; gap: 0.75rem; justify-content: center; margin-top: 1.5rem; }}
      .root-note {{ color: var(--muted); text-align: center; padding: 3rem 1rem; }}
      .honeypot {{ position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }}
    """

  @classmethod
  def _layout(cls, title, body):
    return f"""<!doctype html>
<html lang="en" dir="auto">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{cls._esc(title)}</title>
    <style>{cls._styles()}</style>
  </head>
  <body>
    <header class="top"><a href="/">Stores</a></header>
    <main>{body}</main>
  </body>
</html>
"""

  @classmethod
  def _pager(cls, base, q, page):
    """Previous/next links, keeping the search term."""
    if page["total"] <= page["limit"]:
      return ""

    suffix = f"&q={cls._attr(q)}" if q else ""
    offset = page["offset"]
    limit = page["limit"]
    parts = ['<nav class="pager">']

    if offset > 0:
      parts.append(f'<a href="{base}?offset={max(0, offset - limit)}{suffix}">&larr; Previous</a>')

    if page["has_more"]:
      parts.append(f'<a href="{base}?offset={offset + limit}{suffix}">Next &rarr;</a>')

    parts.append("</nav>")

    return "".join(parts)

  # --- pages ----------------------------------------------------------

  @classmethod
  def directory(cls, stores, q):
    """The root: every store."""
    if not stores["items"]:
      body = "<h1>Stores</h1>"
      body += (
        '<p class="lead">No stores match that search.</p>' if q
        else '<p class="lead">There are no stores yet.</p>'
      )
    else:
      cards = []

      for store in stores["items"]:
        if store["logo"]:
          face = f'<img class="logo" src="{cls._attr(store["logo"])}" alt="" />'
        else:
          face = f'<div class="initial">{cls._esc((store["name"] or "?")[:1].upper())}</div>'

        cards.append(
          f'<a class="card store-card" href="/stores/{cls._attr(store["slug"])}">'
          f'{face}<span class="store-info">'
          f'<span class="name">{cls._esc(store["name"])}</span>'
          '<span class="meta">View products</span></span></a>'
        )

      body = "<h1>Stores</h1>"
      body += f'<div class="store-grid">{"".join(cards)}</div>'
      body += cls._pager("/", q, stores)

    return cls._layout("Stores", body)

  @classmethod
  def store(cls, store, products, q):
    """One store: its products as cards, and a search box."""
    name = cls._esc(store.store_name)

    if store.store_logo:
      head = (
        f'<img class="logo" src="{cls._attr(store.store_logo)}" alt="" '
        'style="width:72px;height:72px;border-radius:14px;object-fit:cover;vertical-align:middle;margin-inline-end:1rem" />'
      )
    else:
      head = ""

    body = f'{head}<h1 style="display:inline-block;vertical-align:middle">{name}</h1>'

    if q:
      body += f'<p class="lead">Showing results for &ldquo;{cls._esc(q)}&rdquo;.</p>'

    body += (
      '<form class="search" method="get" action="">'
      f'<input type="search" name="q" value="{cls._attr(q)}" placeholder="Search products" />'
      '<button type="submit">Search</button></form>'
    )

    if not products["items"]:
      body += (
        '<p class="lead">No products match that search.</p>' if q
        else '<p class="lead">This store has no products yet.</p>'
      )
    else:
      cards = []

      for product in products["items"]:
        if product["image"]:
          face = f'<img class="cover" src="{cls._attr(product["image"])}" alt="" loading="lazy" />'
        else:
          face = '<div class="cover"></div>'

        if product["public_id"]:
          href = f'/pages/{cls._attr(product["public_id"])}'
        else:
          href = f'/stores/{cls._attr(store.store_slug)}/{product["product_id"]}'

        price = (
          f'<span class="price">{product["price"]:,}</span> DA'
          if product["price"] is not None else '<span class="muted">No price</span>'
        )

        cards.append(
          f'<a class="card" href="{href}">{face}<div class="body">'
          f'<p class="title">{cls._esc(product["title"] or "Product " + str(product["product_id"]))}</p>'
          f'<p style="margin:0">{price}</p></div></a>'
        )

      body += f'<div class="grid">{"".join(cards)}</div>'
      body += cls._pager(f"/stores/{cls._attr(store.store_slug)}", q, products)

    return cls._layout(store.store_name, body)

  @classmethod
  def product(cls, store, product, wilayas, communes, can_order, reason,
              values=None, errors=None, message=None):
    """A store's default product page, with the checkout form.

    `values` and `errors` are what the form re-renders with after a rejected
    submit; on a first load they are empty. `message` is a whole-form banner,
    used when the site itself refused the order and the reason is not any one
    field.
    """
    values = values or {}
    errors = errors or {}
    message_html = f'<div class="banner error">{cls._esc(message)}</div>' if message else ""

    title = cls._esc(product.get("title") or f"Product {product['product_id']}")
    images = product.get("images") or []

    gallery = ""
    if images:
      gallery = '<div class="gallery">' + "".join(
        f'<img src="{cls._attr(url)}" alt="" loading="lazy" />' for url in images
      ) + "</div>"

    if product.get("price") is not None:
      price = f'<p class="price" style="font-size:1.6rem">{product["price"]:,} DA</p>'
    else:
      price = '<p class="muted">Price on request</p>'

    stock = (
      '<span class="badge in">In stock</span>' if product.get("available")
      else '<span class="badge out">Out of stock</span>'
    )

    description = ""
    if product.get("description"):
      description = f'<p>{cls._esc(product["description"])}</p>'

    left = (
      f"{gallery}"
      f"<h1>{title}{stock}</h1>"
      f"{price}"
      f"{description}"
    )

    if can_order:
      form = cls._order_form(store, product, wilayas, communes, values, errors)
    else:
      form = f'<p class="lead">{cls._esc(reason)}</p>'

    body = (
      f'<p><a href="/stores/{cls._attr(store.store_slug)}">&larr; {cls._esc(store.store_name)}</a></p>'
      f'{message_html}'
      f'<div class="product"><div>{left}</div><div>{form}</div></div>'
    )

    return cls._layout(product.get("title") or store.store_name, body)

  @classmethod
  def _order_form(cls, store, product, wilayas, communes, values, errors):
    """The checkout form. No price and no quantity: the server decides both."""
    def field(name, label, value=None, kind="text"):
      shown = cls._attr(value if value is not None else values.get(name, ""))
      error = errors.get(name)
      error_html = f'<div class="error">{cls._esc(error)}</div>' if error else ""
      return (
        f'<label class="field"><span>{cls._esc(label)}</span>'
        f'<input type="{kind}" name="{name}" value="{shown}" />{error_html}</label>'
      )

    options = []

    for wilaya in wilayas:
      selected = " selected" if str(values.get("wilaya_id", "")) == str(wilaya.id) else ""
      label = f"{wilaya.number} - {wilaya.name}" if wilaya.number else wilaya.name
      options.append(f'<option value="{wilaya.id}"{selected}>{cls._esc(label)}</option>')

    wilaya_error = errors.get("wilaya_id")
    wilaya_error_html = f'<div class="error">{cls._esc(wilaya_error)}</div>' if wilaya_error else ""

    commune_options = []
    current_wilaya = None

    for commune in communes:
      if commune.wilaya_id != current_wilaya:
        if current_wilaya is not None:
          commune_options.append("</optgroup>")

        parent = next((w for w in wilayas if w.id == commune.wilaya_id), None)
        label = f"{parent.number} - {parent.name}" if parent and parent.number else (
          parent.name if parent else str(commune.wilaya_id)
        )
        commune_options.append(f'<optgroup label="{cls._esc(label)}">')
        current_wilaya = commune.wilaya_id

      selected = " selected" if str(values.get("commune_id", "")) == str(commune.id) else ""
      commune_options.append(
        f'<option value="{commune.id}"{selected}>{cls._esc(commune.name)}</option>'
      )

    if current_wilaya is not None:
      commune_options.append("</optgroup>")

    commune_error = errors.get("commune_id")
    commune_error_html = f'<div class="error">{cls._esc(commune_error)}</div>' if commune_error else ""

    return (
      f'<fieldset><legend>Order this product</legend>'
      f'<form method="post" action="/stores/{cls._attr(store.store_slug)}/{product["product_id"]}/order">'
      f'{field("full_name", "Full name")}'
      f'{field("phone", "Phone", kind="tel")}'
      f'{field("adresse", "Address")}'
      '<label class="field"><span>Wilaya</span>'
      f'<select name="wilaya_id"><option value="">Choose a wilaya</option>{"".join(options)}</select>'
      f'{wilaya_error_html}</label>'
      '<label class="field"><span>Commune</span>'
      f'<select name="commune_id"><option value="">Choose a commune</option>{"".join(commune_options)}</select>'
      f'{commune_error_html}</label>'
      '<div class="honeypot"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off" /></label></div>'
      '<button type="submit">Place order</button>'
      '</form></fieldset>'
    )

  @classmethod
  def success(cls, store, product):
    body = (
      f'<div class="banner ok">Your order has been placed.</div>'
      f'<h1>Thank you</h1>'
      f'<p class="lead">Your order for &ldquo;{cls._esc(product.get("title") or product["product_id"])}&rdquo; '
      f'was sent to {cls._esc(store.store_name)}. They will contact you to confirm.</p>'
      f'<p><a href="/stores/{cls._attr(store.store_slug)}">Back to {cls._esc(store.store_name)}</a></p>'
    )

    return cls._layout("Order placed", body)

  @classmethod
  def error(cls, message, back_href=None, back_label="Go back"):
    link = (
      f'<p><a href="{cls._attr(back_href)}">{cls._esc(back_label)}</a></p>'
      if back_href else ""
    )
    body = f'<div class="banner error">{cls._esc(message)}</div>{link}'

    return cls._layout("Not available", body)

  @classmethod
  def not_found(cls):
    return cls._layout("Not found", '<div class="root-note">There is no store here.</div>')
