# MCP

This project's operations as tools, for an AI agent. A third front end beside the
[CLI](cli.md) and the [HTTP API](http-api.md), over the same services. Today it
reads and writes: look up a product page, keep a catalogue of what it saw, write
landing pages. It does not yet drive a cart or place an order — see
[the tools](#the-tools).

```bash
python main.py mcp            # 127.0.0.1:8001/mcp/
```

Defaults come from `MCP_HOST`, `MCP_PORT` and `MCP_PATH`, and each has a flag:
`main.py mcp --port 9001`. In containers it is the `mcp` service in either compose
stack — see [../start/docker.md](../start/docker.md).

## Two ways in

| | Sign in | An MCP API key |
| --- | --- | --- |
| Good for | Claude, an IDE, anything with a browser | a script, a test, another service |
| Set up | nothing — the connector asks for it | `apikey create --type mcp` |
| Expires | an hour, refreshed silently | when you revoke it |
| Sent as | a bearer token, by the client | `Authorization: Bearer sk_...` |

Either way the tools act as that account, see its cart, and cannot reach another's.

**Sign in is the interesting one.** Claude's connector flow is OAuth 2.1, and this
server is its own authorization server: the connector sends a person to
`/oauth/authorize`, they type their **dashboard** username and password, and the
server hands back a signed token naming them. There is no third-party identity
provider in the middle and no mapping somebody else's account onto yours —
signing in *is* the lookup.

FastMCP does all of the protocol around that: the discovery documents, dynamic
client registration, PKCE, resource binding, Claude's published client identity,
and the short-lived token the connector actually holds. This project supplies the
password check and the tokens it mints.

### Pointing a connector at it

Give it the URL and nothing else — no key, no user name:

```
https://mcp.example.com/mcp/
```

In the connector's **Authentication** section choose **Sign in now** and leave the
OAuth client on the default, *Use Claude's published identity*. Both the server and
`MCP_PUBLIC_URL` must be reachable over **https**; a remote connector refuses
plain HTTP.

`MCP_PUBLIC_URL` has to be the address the outside world uses — your tunnel or
reverse proxy — and it is not the same as `MCP_HOST`, which is what the process
binds inside the container. `main.py mcp` prints the URL to paste and tells you if
it will not work.

The trailing slash on the path matters: the transport is mounted as a prefix, and
a client pointed at `/mcp` without one gets a redirect rather than a session.

### Using a key instead

```bash
python main.py apikey create --type mcp --label "my agent"
```

Then configure the client with a header:

```json
{ "headers": { "Authorization": "Bearer sk_..." } }
```

`Authorization: Bearer`, **not** `X-API-Key`. That is the header OAuth defines and
the only one an MCP client sends; the HTTP API's `X-API-Key` is not read here.

A key of type `api` is refused, and so is a missing one — the connector will not
list the tools until it has signed in.

## What each client gets

The credential identifies the user, and everything follows from that the same way
it does on the API:

- no tool takes a user name — the caller is whoever signed in;
- each key gets its own sawa9ly session, so **two clients never share a cart**;
- landing pages are the caller's own and no tool reaches another's.

## The tools

10 of them, over three resources:

| | |
| --- | --- |
| `get_product` | scrape a sawa9ly.app product page |
| `add_product_to_cart`, `remove_product_from_cart` | add or remove a product in the caller's cart |
| `list_catalogue`, `get_catalogue_product`, `save_catalogue_product` | the saved catalogue — scrape once, read back without a request to the site |
| `list_pages`, `create_page`, `get_page`, `update_page` | landing pages |

**That is not the whole surface, on purpose.** A module exists for every
`/api/v1` resource — cart, checkout, clients, orders, Telegram, trackers — and
`TOOL_GROUPS` in `src/mcp/server.py` is the switchboard: a resource is served when
it is in that tuple. The other six are written and switched off.

So today an agent can look at a product, keep a catalogue of what it saw, and
write landing pages. It **cannot drive a cart or place an order**, which is the
half worth being careful about: an order submitted to sawa9ly.app cannot be
cancelled from here. Turning those resources on is uncommenting an import and a
tuple entry; the module, the per-credential ownership scoping and the sign-in are
already there.

When they are on, both checkout tools take `dry_run`, which stages the cart and
stops before the form, and both describe themselves as irreversible when it is
false. Do a `dry_run` first whenever the quantities, the prices or the recipient
are uncertain — it is the only way to see what the site thinks the order costs
before committing to it.

## Tokens

An access token lasts **an hour** and is refreshed silently by the connector. It is
signed, not stored, so there is no table of them.

**They cannot be revoked one at a time.** A token stops working when it expires,
or immediately for everyone when the signing key is rotated — delete the
`mcp_token` row from `app_secrets` and sign in again. That is the deliberate
trade: a table with per-token revocation would be a second answer to "who is
signed in", and the project already has one, the `users` table. The dashboard's own
session tokens work the same way, for twelve hours.

An API key, if that is what you used, is revocable individually like any other:
`apikey revoke <prefix>`.

## What is different from the HTTP API

One thing, and it is deliberate: `save_catalogue_product` scrapes through **the
caller's own** sawa9ly session. `/api/v1/catalogue/{id}` borrows the first user by
name with complete credentials, because that route carries no authentication and
so knows no caller. A tool call knows whose session it is, so there is nothing
left to borrow one for — and a caller missing their own credentials is told so by
name, with the command to fix it, rather than being quietly served by a stranger's
session.

The other two catalogue tools are the mirror image: the rows belong to no user, so
`list_catalogue` and `get_catalogue_product` resolve the caller for no reason
except to require the credential. They do it anyway — a tool surface where three
local-table tools need no key is a surface where nothing does.

Everything else is the same operation over the same service. A change that adds a
route without adding a tool is unfinished work, in the same way a route without a
CLI command is.
