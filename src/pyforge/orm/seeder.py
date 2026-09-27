class Seeder:
    """Base class for database seeders — ``pyforge db:seed`` runs
    ``database.seeders.database_seeder.DatabaseSeeder().run()`` inside a
    :func:`~pyforge.database.session_scope`, the same auto-committing session
    every HTTP request gets::

        class DatabaseSeeder(Seeder):
            def run(self) -> None:
                UserFactory.create_batch(10)
    """

    def run(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement run().")
