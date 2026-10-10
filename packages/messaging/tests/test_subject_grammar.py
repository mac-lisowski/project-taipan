"""Subject grammar helper: one builder, loud on bad names. No broker.

The spec pins the grammar: names carry domain plus kind plus version.
The expected strings here come from that rule, not from the code.
"""

import pytest
from messaging import dead_letter_subject, subject


def test_subject_joins_domain_kind_and_version() -> None:
    assert subject("orders", "order", "v1") == "orders.order.v1"


def test_dotted_domain_spans_segments() -> None:
    # Domains may own a namespace: jobs.a1b2 stays one domain.
    assert subject("jobs.a1b2", "mail", "v2") == "jobs.a1b2.mail.v2"


def test_dlq_stays_a_kind_of_its_domain() -> None:
    assert dead_letter_subject("orders") == "orders.dlq"
    assert dead_letter_subject("jobs.a1b2") == "jobs.a1b2.dlq"


@pytest.mark.parametrize("kind", ["", " ", "or der", "or.der", "*", ">"])
def test_bad_kind_fails_loud(kind: str) -> None:
    with pytest.raises(ValueError):
        subject("orders", kind, "v1")


@pytest.mark.parametrize("version", ["", " ", "v 1", "v.1", "*"])
def test_bad_version_fails_loud(version: str) -> None:
    with pytest.raises(ValueError):
        subject("orders", "order", version)


@pytest.mark.parametrize("domain", ["", " ", "or der", "or.*", "or.>"])
def test_bad_domain_fails_loud(domain: str) -> None:
    with pytest.raises(ValueError):
        subject(domain, "order", "v1")


def test_dlq_rejects_a_bad_domain() -> None:
    with pytest.raises(ValueError):
        dead_letter_subject("or der")
