"""Formality Atlas: a thin alias of the shared atlas engine (tools/atlas.py, `atlas.py formality ...`). Kept so older imports / commands keep working:
  python tools/formality_atlas.py layout|add|reinforce|describe|near|path|list|requests|resolve ...
The library API (load, save, layout, value_at, neutral, blend_words, describe_value, learn_from_mark, add_request, ...) is atlas.py's, with the formality atlas as the default.
See tools/atlas.py for the data format and the CLI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import *  # noqa: F401,F403,E402
from atlas import FORMALITY_FEATS as FEATS  # noqa: E402,F401
from atlas import ATLAS, ROOT, main as _main  # noqa: E402,F401
import atlas as _a  # noqa: E402


def load(path=None, kind="formality"):
    return _a.load(path, kind)


def neutral(kind="formality"):
    return _a.neutral(kind)


def main(argv):
    return _main(argv, "formality")


if __name__ == "__main__":
    main(sys.argv[1:])
