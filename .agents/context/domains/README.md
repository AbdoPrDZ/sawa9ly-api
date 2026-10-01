# Domains

Business areas with their own rules. Read the file for the area you are changing;
skip the rest.

| Domain | Covers | Read it when |
| --- | --- | --- |
| `authentication.md` | API keys, per-user sawa9ly sessions, credentials, roles | Adding auth, touching keys, debugging "logged out" or a wrong-user cart |
| `orders.md` | Order lifecycle, state machine, the two product ids | Anything touching orders or order lines |
| `checkout.md` | Driving the site's cart and two-step checkout | Touching cart mutation, prices, or submitting an order |
| `catalogue.md` | Saved product info and delivery clients | Touching products, scraped data, or checkout recipient fields |
| `telegram.md` | Linking a user to a chat, and the bot that listens for it | Adding notifications, touching the bot token, or debugging an unlinked chat |
| `notifications.md` | Recording an event and delivering it to the people who asked | Adding a notification event, or debugging a message that did not arrive |
| `i18n.md` | The per-user language, the message catalogues, one row per language, RTL | Writing or changing any text a person reads, or adding a language |

## Boundaries

- **Orders** own local intent — what should be ordered, at what quantity and
  price, and in what state. They do not talk to the site directly; they go
  through `Cart`.
- **Checkout** owns the interaction with the site. It knows about components and
  snapshots. It knows nothing about orders.
- **Catalogue** is reference data. Products describe what exists; clients describe
  where to deliver. Both are inputs to an order, never part of one.
- **Authentication** owns identity. Everything downstream takes a `Livewire` and
  does not care where it came from.
- **Telegram** is outbound only, and optional. It reads a user's binding and
  sends; it never affects what an order is or what it costs, and with no bot
  token set nothing in the rest of the app changes.
- **Notifications** is the join between something the queue noticed and the people
  who asked to hear about it. It reads trackers and products; it changes neither,
  and a failed send never fails a pass.
- **i18n** is cross-cutting and owns no data of its own beyond the per-user
  language. It decides *which words*, not what anything means; a notification's
  judgement about what is worth saying stays in `notifications.md`, and a
  controller's response shape stays in `schemas.py`.

The dependency arrow points one way: catalogue → orders → checkout. Nothing in
checkout imports an order, which is what keeps the site's quirks isolated to one
file.
