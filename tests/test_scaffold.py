"""F0 scaffold smoke: package is importable."""

from __future__ import annotations


def test_nanhu_package_importable() -> None:
    import nanhu

    assert nanhu.__version__
