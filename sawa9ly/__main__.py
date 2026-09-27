"""`python -m sawa9ly <command> [args]` — the same CLI as `python main.py`.

`App.main()` is the one implementation. This and `main.py` are two doors onto
it, not two parsers: adding a command group touches `cli/`, and both entry
points pick it up.
"""

from cli.app import App

if __name__ == "__main__":
  App.main()
