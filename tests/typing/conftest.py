"""Keep pytest from collecting the typing case files (they intentionally contain
type errors and are meant to be fed to the type checkers, not imported)."""

collect_ignore_glob = ["cases/*"]
