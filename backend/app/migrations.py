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
MULTI_SEED_STUDY_MIGRATION_ID = "20261003_01_multi_seed_evaluation"
EXTERNAL_VALIDATION_MIGRATION_ID = "20261003_02_external_validation"



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
        if not dataset_version_applied:
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

        study_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": MULTI_SEED_STUDY_MIGRATION_ID},
        ).scalar()
        if not study_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS multi_seed_studies (
                    id VARCHAR(36) PRIMARY KEY,
                    base_experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id),
                    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    status VARCHAR(24) NOT NULL DEFAULT 'created',
                    operation_key VARCHAR(128) NOT NULL UNIQUE,
                    requested_seeds JSON NOT NULL,
                    completed_seeds JSON NOT NULL DEFAULT '[]',
                    failed_seeds JSON NOT NULL DEFAULT '[]',
                    cancelled_seeds JSON NOT NULL DEFAULT '[]',
                    model_identities JSON NOT NULL,
                    locked_config JSON NOT NULL,
                    configuration_fingerprint VARCHAR(64) NOT NULL,
                    protocol_version VARCHAR(32) NOT NULL DEFAULT 'multi_seed_evaluation_v1',
                    aggregate_summary JSON NOT NULL DEFAULT '{}',
                    limitations JSON NOT NULL DEFAULT '[]',
                    reproducibility_metadata JSON NOT NULL DEFAULT '{}',
                    study_artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    failure JSON,
                    created_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_base_experiment_id ON multi_seed_studies(base_experiment_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_dataset_id ON multi_seed_studies(dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_dataset_version_id ON multi_seed_studies(dataset_version_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_status ON multi_seed_studies(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_operation_key ON multi_seed_studies(operation_key)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_configuration_fingerprint ON multi_seed_studies(configuration_fingerprint)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_study_artifact_id ON multi_seed_studies(study_artifact_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_multi_seed_studies_created_at ON multi_seed_studies(created_at)"))

            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS study_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    study_id VARCHAR(36) NOT NULL REFERENCES multi_seed_studies(id),
                    run_id VARCHAR(36) REFERENCES runs(id),
                    job_id VARCHAR(36) REFERENCES jobs(id),
                    seed INTEGER NOT NULL,
                    seed_order INTEGER NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'created',
                    failure JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    CONSTRAINT uq_study_runs_study_seed UNIQUE(study_id, seed)
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_study_runs_study_id ON study_runs(study_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_study_runs_run_id ON study_runs(run_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_study_runs_job_id ON study_runs(job_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_study_runs_status ON study_runs(status)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": MULTI_SEED_STUDY_MIGRATION_ID, "applied_at": utcnow()},
            )

        ext_val_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": EXTERNAL_VALIDATION_MIGRATION_ID},
        ).scalar()
        if not ext_val_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS external_validations (
                    id VARCHAR(36) PRIMARY KEY,
                    model_id VARCHAR(36) NOT NULL REFERENCES models(id),
                    run_id VARCHAR(36) REFERENCES runs(id),
                    experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id),
                    training_dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    training_dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    external_dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    external_dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    study_id VARCHAR(36) REFERENCES multi_seed_studies(id),
                    study_seed INTEGER,
                    status VARCHAR(24) NOT NULL DEFAULT 'created',
                    operation_key VARCHAR(128) NOT NULL UNIQUE,
                    compatibility JSON NOT NULL DEFAULT '{}',
                    label_mapping JSON NOT NULL DEFAULT '{}',
                    threshold_metadata JSON NOT NULL DEFAULT '{}',
                    metrics JSON NOT NULL DEFAULT '{}',
                    internal_metrics JSON NOT NULL DEFAULT '{}',
                    comparison JSON NOT NULL DEFAULT '{}',
                    generalization_gap JSON NOT NULL DEFAULT '{}',
                    provenance JSON NOT NULL DEFAULT '{}',
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    limitations JSON NOT NULL DEFAULT '[]',
                    warnings JSON NOT NULL DEFAULT '[]',
                    failure JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_model_id ON external_validations(model_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_run_id ON external_validations(run_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_experiment_id ON external_validations(experiment_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_training_dataset_id ON external_validations(training_dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_external_dataset_id ON external_validations(external_dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_status ON external_validations(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_operation_key ON external_validations(operation_key)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_artifact_id ON external_validations(artifact_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_external_validations_created_at ON external_validations(created_at)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": EXTERNAL_VALIDATION_MIGRATION_ID, "applied_at": utcnow()},
            )
