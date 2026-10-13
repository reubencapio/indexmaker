"""The shared store of company details, and the job that fills it."""

from datetime import datetime, timedelta, timezone

import pytest
from indexforge import Constituent, DataSourceError
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.company import CompanyDetail
from app.services.company_store import DatabaseCompanyStore, fill_company_details
from tests.conftest import TEST_DATABASE_URL

SOURCE = "Test Market"
WEEK = timedelta(days=7)


@pytest.fixture
def store():
    # The store commits its own transactions, as it does in a build, so these
    # tests use a real connection and clear the table around each test.
    engine = create_engine(TEST_DATABASE_URL.replace("+asyncpg", ""), poolclass=NullPool)
    sessions = sessionmaker(bind=engine)

    def clear():
        with sessions() as db:
            db.execute(delete(CompanyDetail))
            db.commit()

    clear()
    store = DatabaseCompanyStore(sessions)
    store.sessions = sessions
    yield store
    clear()
    engine.dispose()


def company(ticker, description="Makes things."):
    return Constituent(
        ticker=ticker,
        name=f"{ticker} Corp",
        market_cap=5e9,
        country="Germany",
        sector="Technology",
        business_description=description,
    )


def age(store, ticker, days):
    with store.sessions() as db:
        db.execute(
            update(CompanyDetail)
            .where(CompanyDetail.ticker == ticker)
            .values(fetched_at=datetime.now(timezone.utc) - timedelta(days=days))
        )
        db.commit()


def test_details_round_trip_per_source(store):
    store.put(SOURCE, [company("AAA", "Builds qubits."), company("BBB")])

    found = store.get(SOURCE, ["AAA", "BBB", "CCC"], WEEK)

    assert set(found) == {"AAA", "BBB"}
    assert found["AAA"].business_description == "Builds qubits."
    assert found["AAA"].country == "Germany"
    assert store.get("Another Source", ["AAA"], WEEK) == {}


def test_stale_details_are_not_returned(store):
    store.put(SOURCE, [company("AAA")])
    age(store, "AAA", 8)

    assert store.get(SOURCE, ["AAA"], WEEK) == {}


def test_storing_again_replaces(store):
    store.put(SOURCE, [company("AAA", "Old.")])
    store.put(SOURCE, [company("AAA", "New.")])

    assert store.get(SOURCE, ["AAA"], WEEK)["AAA"].business_description == "New."


def test_wanted_companies_come_first_then_the_stalest(store):
    store.put(SOURCE, [company("FRESH"), company("OLD"), company("OLDER")])
    age(store, "OLD", 8)
    age(store, "OLDER", 30)
    store.want(SOURCE, ["NEEDED"])

    assert store.due(SOURCE, 10) == ["NEEDED", "OLDER", "OLD"]
    assert store.due(SOURCE, 1) == ["NEEDED"]
    # A wanted company with no details is not handed to a build.
    assert store.get(SOURCE, ["NEEDED"], WEEK) == {}


def test_wanting_a_stored_company_keeps_its_details(store):
    store.put(SOURCE, [company("AAA")])
    store.want(SOURCE, ["AAA"])

    assert "AAA" in store.get(SOURCE, ["AAA"], WEEK)
    assert store.due(SOURCE, 10) == ["AAA"]


class Source:
    """Answers for known tickers until told to stop."""

    def __init__(self, known, answers_left=10_000):
        self.known = set(known)
        self.answers_left = answers_left
        self.requested = []

    def get_name(self):
        return SOURCE

    def get_constituent_data(self, tickers, as_of_date=None):
        if self.answers_left <= 0:
            raise DataSourceError("limiting requests")
        self.answers_left -= 1
        self.requested.extend(tickers)
        return [company(t) if t in self.known else Constituent(ticker=t, name=t) for t in tickers]


def test_fill_fetches_what_is_due_and_forgets_unknown_tickers(store):
    store.want(SOURCE, ["AAA", "BBB", "TYPO"])

    result = fill_company_details(Source({"AAA", "BBB"}), store, limit=50)

    assert result == {"status": "completed", "fetched": 2, "unknown": 1, "due": 3}
    assert set(store.get(SOURCE, ["AAA", "BBB", "TYPO"], WEEK)) == {"AAA", "BBB"}
    assert store.due(SOURCE, 10) == []
    with store.sessions() as db:
        assert db.scalars(select(CompanyDetail.ticker).order_by(CompanyDetail.ticker)).all() == [
            "AAA",
            "BBB",
        ]


def test_fill_respects_its_limit(store):
    store.want(SOURCE, [f"T{i:02d}" for i in range(40)])
    source = Source({f"T{i:02d}" for i in range(40)})

    fill_company_details(source, store, limit=30)

    assert len(source.requested) == 30
    assert len(store.due(SOURCE, 100)) == 10


def test_fill_stops_when_the_source_limits_and_keeps_what_it_got(store):
    tickers = [f"T{i:02d}" for i in range(60)]
    store.want(SOURCE, tickers)

    result = fill_company_details(Source(set(tickers), answers_left=1), store, limit=60)

    assert result["status"] == "limited" and result["fetched"] == 25
    assert len(store.due(SOURCE, 100)) == 35
