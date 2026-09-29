# Notifications

Something the queue noticed, worth telling people about. A notification is a
**record of an event**, and creating that record is what sends it.

| | |
| --- | --- |
| `src/models/notification.py` | the event, and the fan-out that sends it |
| `src/models/notification_delivery.py` | one person's copy, and whether it arrived |
| `src/services/notifications.py` | which events exist, what they say, who hears |
| Dispatch | `Tracking._notify` in `src/services/tracking.py` |

## Why two tables

`notifications` holds **no recipient**. One availability change is one row however
many people are watching that product; the fan-out is a row per person in
`notification_deliveries`, under `UNIQUE(notification_id, user_id)`.

That is what makes the two properties hold at once:

- **one event, one message per person.** Four tracker rows pointing at one product
  is one fact. The unique constraint makes the duplicate impossible rather than
  merely unlikely.
- **retry is safe.** With a single `sent_at` on the event, one blocked chat would
  make the whole send look failed, and retrying it would resend to everybody who
  already received it. Per-person outcome is what makes "try again" mean "try
  again" and not "send it all again".

`Notification` (the event) answers *what happened*. `NotificationDelivery` answers
*who has been told yet*. The second outlives the product: the FK is `SET NULL` and
`body` keeps the text verbatim, so the record stays readable after the product is
gone — which is the right outcome for something a user was told.

## Creating one is sending it

`Notification.create(...)` writes the row and then delivers it. Doing both in one
place is deliberate: a message that was never written cannot be accounted for, and
a row written but never sent is one nobody looks at.

`send_to` is idempotent per person, and `deliver` is the **only** place a message
is put on its way, so nothing can send twice by two paths.

## Failures are data, not exceptions

Nothing here raises for a delivery problem. Every outcome is kept:

| Situation | Recorded as |
| --- | --- |
| Delivered | `sent_at` set |
| Chat refused it | `send_error` = Telegram's reason, `chat_id` kept |
| No linked chat | `send_error` = "no Telegram chat is linked…" |

The last one matters for retry: a user with **no linked chat** was not held back
by a failure, they had nowhere to go because they had not opted in. Sending it an
hour later is not delivering news, it is inventing it — so `undelivered()`
defaults to `retryable=True`, which excludes exactly that case. A chat that was
there and *refused* is different, and is retried.

Retry is also **bounded by age** (`RETRY_WITHIN_SECONDS`, one hour). A notification
says what was true when it was noticed, and stock goes back in stock: telling
somebody now that a product went out of stock three days ago is worse than telling
them nothing, because it is confidently wrong. An event past the window is left
undelivered and stays a record.

## Not an error for the queue

A notification failure is reported in the pass's `notify_errors` and deliberately
**not** in `errors`, because `errors` is what makes `cron run` exit non-zero. The
scan did its job; a chat that was blocked says nothing about whether the product
went out of stock. A queue that reports failure every time one person mutes a bot
teaches you to ignore its exit code, which is the only thing a scheduler reads.

A missing `TELEGRAM_BOT_TOKEN` is the same: notifications are optional, so the
pass records why nobody was told **once** and carries on.

## The event

One kind: **a watched product changed**. `Tracking` already diffs each scrape
against the stored row, so the previous value is in hand and the dispatch sits in
`Tracking._notify`.

| Kind | Fires on |
| --- | --- |
| `product.changed` | `available` or `price` differing from the stored value |

### One message per product per fetch

A scrape that finds the price and the stock both different is **one thing that
happened once**. An earlier version raised one event per changed field and sent
two messages about a single change — the sort of thing that gets a bot muted. Each
change now gets its own line inside one message:

```
Product 5663 changed:

Product 5663 is no longer available. It has gone out of stock.

Price dropped to 14,500. It was 16,000.

Projecteur portable Full HD HY300 Mini Android 11
https://sawa9ly.app/product/5663

You are watching this product.
```

One change keeps its own headline, because "it is back in stock" beats
"something changed". The kind is one value, not one per field: which fields moved
belongs in the body, where a reader wants it, not in a column they have to join
back together.

### Price is compared as a number, never as text

The site writes prices the way it displays them, and may print `16,000 دج` one
minute and `16.000 دج` the next. Diffing the stored string would put a message in
somebody's chat about a comma, so `Notifications._price_line` runs both through
`Product.parse_price` and compares the figures, returning **None** when they match
— a field can be in the diff and still be nothing. `parse_price` disambiguates the
two separator conventions by position and keeps only the whole part.

`None` is a value, not a gap: a price that disappears — "sur demande" — and one
that comes back are both events, because for somebody reselling the product that
is exactly the news. Each gets its own wording rather than a null in the text.

Each line says **which way** and **from what**. A new number with no "was" beside
it is not news anybody can act on, because the reader cannot tell a rise from a
fall or a change from a typo.

### What is worth saying

`NOTIFIABLE_FIELDS` is `("available", "price")`, written out and deliberately not
derived. A title or description change is recorded in the diff and reported by the
pass, but whether that is worth interrupting somebody for is a judgement this code
should not make on its own. Adding a field means adding a `_line` branch here and
one entry in that tuple.

`Notification.KIND_PRODUCT_CHANGED` is a plain string, not an enum, because the set
will grow and an unfamiliar value is better than a migration every time somebody
adds a second one.

### Testing against a real database

**Never flip the availability or price of a product a real user is watching.** The
catalogue is live, and a flip on a watched product is a real notification to a
real chat — which is how this feature's own tests ended up messaging the operator
more than once. Use a sawa9ly id nothing tracks, e.g. `999999`, and delete the row
afterwards.
