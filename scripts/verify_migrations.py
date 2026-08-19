# pyright: reportMissingImports=false

from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine


def main() -> None:
    config = Config("alembic.ini")
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise SystemExit(
            f"Expected exactly one Alembic head, found: {', '.join(heads)}"
        )

    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "migration-test.db"
        database_url = f"sqlite:///{database_path}"
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")

        with create_engine(database_url).connect() as connection:
            current_revision = MigrationContext.configure(
                connection
            ).get_current_revision()

        if current_revision != heads[0]:
            raise SystemExit(
                f"Expected database at {heads[0]}, found {current_revision}"
            )

        command.downgrade(config, "base")

    print(f"Verified linear Alembic history through {heads[0]}")


if __name__ == "__main__":
    main()
