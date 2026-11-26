"""Helpers imported only by tests and measurement scripts.

Nothing in the running application imports this module. It lives in
``epocha.common`` because the shape guards of two apps (``economy`` and
``world``) use it, and putting it inside one app's ``tests`` package would
make the other app import that app's tests.

``case_update_rows`` counts the rows written by each ``bulk_update``
statement. The count is the number of ``WHEN`` branches divided by the
number of updated fields: Django 5.1 ``QuerySet.bulk_update`` writes one
``When(pk=...)`` branch per object per field, and on PostgreSQL the cast
around each ``CASE`` renders as ``(CASE WHEN ...)::type`` (verified in the
source of the project image), so a statement over N rows and F fields
contains N * F ``WHEN`` keywords.
"""

from __future__ import annotations


def case_update_rows(captured_queries, model, field_count: int) -> list[int]:
    """Return the row count of each ``bulk_update`` statement, in execution order.

    Args:
        captured_queries: ``CaptureQueriesContext.captured_queries``.
        model: the model whose table the statements update.
        field_count: the number of fields passed to ``bulk_update``.

    Returns:
        One integer per captured statement that starts with
        ``UPDATE "<table>"`` and contains ``CASE WHEN``.
    """
    prefix = f'UPDATE "{model._meta.db_table}"'
    return [
        query["sql"].count("WHEN") // field_count
        for query in captured_queries
        if query["sql"].startswith(prefix) and "CASE WHEN" in query["sql"]
    ]
