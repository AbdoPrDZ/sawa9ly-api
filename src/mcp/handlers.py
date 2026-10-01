"""The sign-in page and token endpoint, as ASGI handlers.

Kept apart from `authorization.py`, which owns the tokens and the page's markup,
because this is a different job: these functions read an HTTP request, check what
arrived, and answer. Splitting them means the protocol surface — what a valid
request looks like, and what a refusal says — is readable on its own.

Everything the proxy sends here is attacker-influenced, because an authorize URL
can be crafted by anyone. So the checks below are all "is this consistent",
never "is this well-formed and therefore fine": the redirect URI must be the one
the proxy registered, the challenge must be one we issued, and the code must be
one we minted and have not spent.
"""

import hmac

from src.mcp.authorization import AuthorizationError, AuthorizationServer
#: Query and form fields carried through the sign-in form, in the order they are
#: re-emitted. The proxy needs `redirect_uri`, `client_id`, `state`,
#: `code_challenge` and `code_challenge_method` back verbatim to finish the flow.
CARRIED = (
  "response_type",
  "client_id",
  "redirect_uri",
  "state",
  "scope",
  "resource",
  "code_challenge",
  "code_challenge_method",
)


def carried(params):
  """The OAuth fields worth keeping across the form post."""
  return {name: params[name] for name in CARRIED if params.get(name)}


async def authorize(request, server):
  """GET renders the sign-in form; POST checks it and hands back a code.

  The form posts to itself rather than to the proxy, so a failed password
  re-renders instead of leaving a dead end: the person stays on the page with the
  error and the OAuth parameters intact.
  """
  params = carried(dict(request.query_params))

  if request.method == "GET":
    return server.page_response(server.sign_in_page(params))

  form = await request.form()
  username, password = form.get("username", ""), form.get("password", "")
  user = server.authenticate(username, password)

  if user is None:
    # Same page, same fields, one message. Deliberately not distinguishing a
    # missing account from a wrong password, and not saying which was wrong.
    return server.page_response(
      server.sign_in_page(params, error=AuthorizationServer.BAD_CREDENTIALS),
      status=401,
    )

  redirect_uri = form.get("redirect_uri")
  code_challenge = form.get("code_challenge")

  if not redirect_uri or not code_challenge:
    return server.error_response(
      400, "invalid_request", "The sign-in form was missing its OAuth parameters."
    )

  # The code carries the user, the challenge and the redirect URI it was issued
  # against. Signed, so the token endpoint can trust all three without a table,
  # and short-lived, so a code captured from a redirect is worthless within minutes.
  try:
    code = server.issue_code(
      user, code_challenge, redirect_uri, form.get("code_challenge_method", "S256")
    )
  except AuthorizationError as error:
    return server.error_response(400, "invalid_request", str(error))

  return server.redirect(
    server.location_with(redirect_uri, code=code, state=form.get("state"))
  )


async def token(request, server):
  """Exchange an authorization code, or a refresh token, for an access token.

  The proxy is the only caller in practice, but the client id is checked anyway:
  this endpoint issues credentials, and "only our proxy calls it" is a fact about
  the network rather than about the request.
  """
  form = await request.form()
  grant = form.get("grant_type")

  client_id, _secret = server.credentials()

  if form.get("client_id") not in (None, client_id):
    return server.error_response(401, "invalid_client", "Unknown client.")

  if grant == "authorization_code":
    return _code_grant(server, form)

  if grant == "refresh_token":
    return _refresh_grant(server, form)

  return server.error_response(
    400, "unsupported_grant_type", "Use authorization_code or refresh_token."
  )


def _code_grant(server, form):
  """The authorization-code exchange, PKCE and all."""
  record = server.redeem_code(form.get("code", ""))

  if record is None:
    return server.error_response(
      400, "invalid_grant", "That authorization code is not valid, or has expired."
    )

  verifier = form.get("code_verifier", "")
  challenge = AuthorizationServer._code_challenge(verifier)

  if not verifier or not hmac.compare_digest(challenge, record["challenge"]):
    return server.error_response(
      400, "invalid_grant", "The code verifier does not match the challenge."
    )

  # RFC 6749 §4.1.3: when the authorization request carried a redirect URI, the
  # token request has to carry the same one. Checked only when both are present,
  # because the proxy is entitled to omit it having already bound it to the
  # transaction it recorded — and a check that fails on an absent field would be a
  # check that fails on a correct request.
  offered = form.get("redirect_uri")

  if offered and record["redirect_uri"] and not hmac.compare_digest(
    str(offered), str(record["redirect_uri"])
  ):
    return server.error_response(
      400, "invalid_grant", "The redirect URI does not match the one authorized."
    )

  user = server.user_of(record["user_id"])

  if user is None:
    # Signed in, then deleted before the code was redeemed. Revoking a user has
    # to take effect here and not only at the next login.
    return server.error_response(
      400, "invalid_grant", "That account no longer exists."
    )

  return server.json_response(
    {
      "access_token": server.issue_access_token(user),
      "refresh_token": server.issue_refresh_token(user),
      "token_type": "Bearer",
      "expires_in": AuthorizationServer.ACCESS_TTL,
    }
  )


def _refresh_grant(server, form):
  """Swap a refresh token for a new pair, rotating both."""
  user_id = server.verify_refresh_token(form.get("refresh_token", ""))

  if user_id is None:
    return server.error_response(
      400, "invalid_grant", "That refresh token is not valid, or has expired."
    )

  user = server.user_of(user_id)

  if user is None:
    return server.error_response(
      400, "invalid_grant", "That account no longer exists."
    )

  return server.json_response(
    {
      "access_token": server.issue_access_token(user),
      "refresh_token": server.issue_refresh_token(user),
      "token_type": "Bearer",
      "expires_in": AuthorizationServer.ACCESS_TTL,
    }
  )
