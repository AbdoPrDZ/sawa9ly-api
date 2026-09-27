"""Installed entry point for the sawa9ly client.

The import name for the `sawa9ly-api` distribution. It exists so that
`python -m sawa9ly <command>` and the `sawa9ly` console script work from an
install, while `python main.py <command>` keeps working from a checkout.

The CLI is deliberately not re-exported here. `__main__.py` imports
`cli.app.App` directly, so a reader can see which module owns the parser
rather than following a barrel.
"""
