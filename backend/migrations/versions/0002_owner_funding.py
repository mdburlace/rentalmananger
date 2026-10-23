"""Owner contributions and drawings

Adds transactions.owner_id and the two owner-funding categories to every
existing portfolio.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

NEW_CATEGORIES = [
    ("Owner contribution", "owner_contribution", "owner contribution, funds introduced, capital contribution, top up, top-up", 950),
    ("Owner drawing", "owner_drawing", "owner drawing, drawing, distribution to owner", 960),
]


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.create_index("ix_transactions_owner_id", ["owner_id"])
        batch.create_foreign_key("fk_transactions_owner_id", "owners", ["owner_id"], ["id"], ondelete="SET NULL")

    conn = op.get_bind()
    portfolios = [r[0] for r in conn.execute(sa.text("SELECT id FROM portfolios"))]
    for pid in portfolios:
        for name, key, keywords, order in NEW_CATEGORIES:
            exists = conn.execute(sa.text("SELECT 1 FROM categories WHERE portfolio_id=:p AND ato_key=:k"),
                                  {"p": pid, "k": key}).first()
            if not exists:
                conn.execute(sa.text(
                    "INSERT INTO categories (portfolio_id, name, ato_key, keywords, archived, sort_order) "
                    "VALUES (:p, :n, :k, :kw, :a, :o)"), {"p": pid, "n": name, "k": key, "kw": keywords, "a": False, "o": order})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE transactions SET owner_id=NULL"))
    with op.batch_alter_table("transactions") as batch:
        batch.drop_constraint("fk_transactions_owner_id", type_="foreignkey")
        batch.drop_index("ix_transactions_owner_id")
        batch.drop_column("owner_id")
