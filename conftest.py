import warnings

# langgraph 0.2.x creates LC_REVIVER = Reviver() at module level in
# langgraph.checkpoint.serde.jsonplus. Reviver.__init__ calls warn_deprecated()
# when allowed_objects is not provided (langchain_core 0.3.85+). This warning
# fires during conftest collection (when tests/conftest.py imports app.main which
# imports the pipeline graph). Patch Reviver here at module load time — root
# conftest.py is imported before tests/conftest.py, so the patch is in place
# before any langgraph imports trigger.
try:
    from langchain_core.load.load import Reviver as _Reviver

    _orig_reviver_init = _Reviver.__init__

    def _patched_reviver_init(self, *a, **kw) -> None:  # noqa: ANN001
        kw.setdefault("allowed_objects", "core")
        _orig_reviver_init(self, *a, **kw)

    _Reviver.__init__ = _patched_reviver_init  # type: ignore[method-assign]
except Exception:  # noqa: BLE001
    pass
