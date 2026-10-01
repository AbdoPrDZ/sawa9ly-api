# MCP

This project's operations as tools, for an AI agent. A third front end beside the
[CLI](cli.md) and the [HTTP API](http-api.md), over the same services. Today it
reads and writes: look up a product page, keep a catalogue of what it saw, write
landing pages. It does not yet drive a cart or place an order — see
[the tools](#the-tools).

```bash
python main.py apikey create --type mcp     # the client needs a key
python main.py mcp                          # 127.0.0.1:8001/mcp/
```

Defaults come from `MCP_HOST`, `MCP_PORT` and `MCP_PATH`, and each has a flag:
`main.py mcp --port 9001`. In containers it is the `mcp` service in either compose
stack — see [../start/docker.md](../start/docker.md).

## Pointing a client at it

The server speaks MCP over streamable HTTP at `http://127.0.0.1:8001/mcp/`. The
client needs the URL and the key, and nothing else — no user name, because the
server has no user of its own:

```json
{
  "mcpServers": {
    "sawa9ly": {
      "url": "http://127.0.0.1:8001/mcp/",
      "headers": { "X-API-Key": "sk_..." }
    }
  }
}
```

`Authorization: Bearer sk_...` works as well.

**The trailing slash on the path matters.** The transport is mounted as a prefix,
and a client pointed at `/mcp` without one gets a redirect rather than a session.

## The key is a different kind of key

`--type mcp` is not decoration. An API key is refused by the MCP server and an MCP
key is refused by `/api` — including `/api/admin`. They are separate because they
are handed to different things: an API key is typed into a script by its owner,
while an MCP key is typed into an AI agent's client configuration, which means it
lands in transcripts, tool arguments and whatever context the model is given, and
it cannot be scoped down per-call the way a shell variable can. One key accepted
by both surfaces would put `/api/admin` behind a token that is by construction read
by a language model.

A key of the wrong type is reported as *unknown*, exactly like a string that was
never a key, so a refused key cannot be used to confirm that somebody else's
credential exists.

## What each client gets

The key identifies the user, and everything follows from that the same way it does
on the API:

- no tool takes a user name — the caller is whoever's key was presented;
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
tuple entry; the module, the per-key auth and the ownership scoping are already
there.

When they are on, both checkout tools take `dry_run`, which stages the cart and
stops before the form, and both describe themselves as irreversible when it is
false. Do a `dry_run` first whenever the quantities, the prices or the recipient
are uncertain — it is the only way to see what the site thinks the order costs
before committing to it.

## `tools/list` is not authenticated

Anything that can reach the port sees all 10 tool names and descriptions without
presenting a key. Every tool *call* needs one; the catalogue of tools does not.

That is how MCP servers normally behave, and it is why `MCP_HOST` defaults to
loopback and the compose stack publishes it on `127.0.0.1`. To reach it from
another machine, put something in front of it that checks the key.

## What is different from the HTTP API

One thing, and it is deliberate: `save_catalogue_product` scrapes through **the
caller's own** sawa9ly session. `/api/v1/catalogue/{id}` borrows the first user by
name with complete credentials, because that route carries no authentication and
so knows no caller. A tool call knows whose session it is, so there is nothing
left to borrow one for — and a caller missing their own credentials is told so by
name, with the command to fix it, rather than being quietly served by a stranger's
session.

The other two catalogue tools are the mirror image: the rows belong to no user,
so `list_catalogue` and `get_catalogue_product` resolve the caller for no reason
except to require the credential. They do it anyway — a tool surface where three
local-table tools need no key is a surface where nothing does.

Everything else is the same operation over the same service. A change that adds a
route without adding a tool is unfinished work, in the same way a route without a
CLI command is.
