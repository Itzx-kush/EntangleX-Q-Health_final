"""Small, explicit SQLite migrations for the existing local research registry.

The project historically initialized tables with ``create_all``.  Migrations
therefore remain deliberately dependency-free and additive: they never drop,
rename, or rewrite historical rows.
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from .database import engine
from .utils.serialization import utcnow


MIGRATION_ID = "20261002_01_experiment_run_artifact"
MANIFEST_MIGRATION_ID = "20261002_02_immutable_run_manifest"
DATASET_VERSION_MIGRATION_ID = "20261002_03_dataset_versioning"


def _columns(connection, table: str) -> set[str]:
    return {column["name"] for column in inspect(connection).get_columns(table)}


def apply_migrations() -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "id VARCHAR(100) PRIMARY KEY, applied_at DATETIME NOT NULL)"
        ))
        applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": MIGRATION_ID},
        ).scalar()
        if not applied:
            additions = {
                "jobs": "ALTER TABLE jobs ADD COLUMN run_id VARCHAR(36) REFERENCES runs(id)",
                "models": "ALTER TABLE models ADD COLUMN run_id VARCHAR(36) REFERENCES runs(id)",
                "explanations": "ALTER TABLE explanations ADD COLUMN run_id VARCHAR(36) REFERENCES runs(id)",
            }
            for table, statement in additions.items():
                if "run_id" not in _columns(connection, table):
                    connection.execute(text(statement))

            # These access paths are used by run detail and lineage queries.  The
            # partial unique index permits any number of honest legacy NULL rows.
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_run_id ON jobs(run_id) WHERE run_id IS NOT NULL"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_models_run_id ON models(run_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_explanations_run_id ON explanations(run_id)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": MIGRATION_ID, "applied_at": utcnow()},
            )

        manifest_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": MANIFEST_MIGRATION_ID},
        ).scalar()
        if not manifest_applied:
            run_columns = _columns(connection, "runs")
            manifest_additions = {
                "manifest_artifact_id": "ALTER TABLE runs ADD COLUMN manifest_artifact_id VARCHAR(36) REFERENCES artifacts(id)",
                "configuration_fingerprint": "ALTER TABLE runs ADD COLUMN configuration_fingerprint VARCHAR(64)",
                "reproducibility_status": "ALTER TABLE runs ADD COLUMN reproducibility_status VARCHAR(40)",
                "manifest_locked_at": "ALTER TABLE runs ADD COLUMN manifest_locked_at DATETIME",
            }
            for column, statement in manifest_additions.items():
                if column not in run_columns:
                    connection.execute(text(statement))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_runs_manifest_artifact_id ON runs(manifest_artifact_id) WHERE manifest_artifact_id IS NOT NULL"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_runs_configuration_fingerprint ON runs(configuration_fingerprint)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_runs_reproducibility_status ON runs(reproducibility_status)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": MANIFEST_MIGRATION_ID, "applied_at": utcnow()},
            )

        dataset_version_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DATASET_VERSION_MIGRATION_ID},
        ).scalar()
        if dataset_version_applied:
            return
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS dataset_versions (
                id VARCHAR(36) PRIMARY KEY,
                dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                version_number INTEGER NOT NULL,
                version_label VARCHAR(24) NOT NULL,
                content_sha256 VARCHAR(64) NOT NULL,
                schema_fingerprint VARCHAR(64) NOT NULL,
                version_signature VARCHAR(64) NOT NULL,
                row_count INTEGER NOT NULL,
                feature_count INTEGER NOT NULL,
                target VARCHAR(100) NOT NULL,
                positive_label VARCHAR(64) NOT NULL,
                negative_label VARCHAR(64) NOT NULL,
                target_type VARCHAR(40) NOT NULL DEFAULT 'binary_classification',
                class_distribution JSON NOT NULL,
                source_metadata JSON NOT NULL,
                provenance JSON NOT NULL,
                quality_summary JSON NOT NULL,
                storage_reference VARCHAR(320) NOT NULL,
                status VARCHAR(24) NOT NULL DEFAULT 'ready',
                immutable BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                CONSTRAINT uq_dataset_versions_number UNIQUE(dataset_id, version_number),
                CONSTRAINT uq_dataset_versions_signature UNIQUE(dataset_id, version_signature)
            )
        """))
        if "current_version_id" not in _columns(connection, "datasets"):
            connection.execute(text("ALTER TABLE datasets ADD COLUMN current_version_id VARCHAR(36) REFERENCES dataset_versions(id)"))
        if "dataset_version_id" not in _columns(connection, "runs"):
            connection.execute(text("ALTER TABLE runs ADD COLUMN dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_datasets_current_version_id ON datasets(current_version_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_versions_dataset_id ON dataset_versions(dataset_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_versions_content_sha256 ON dataset_versions(content_sha256)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_versions_schema_fingerprint ON dataset_versions(schema_fingerprint)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_versions_status ON dataset_versions(status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_versions_created_at ON dataset_versions(created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_runs_dataset_version_id ON runs(dataset_version_id)"))
        connection.execute(
            text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
            {"id": DATASET_VERSION_MIGRATION_ID, "applied_at": utcnow()},
        )