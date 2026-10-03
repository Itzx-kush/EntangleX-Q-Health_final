"""Small, explicit SQLite migrations for the existing local research registry.

The project historically initialized tables with ``create_all``.  Migrations
therefore remain deliberately dependency-free and additive: they never drop,
rename, or rewrite historical rows.
"""

from __future__ import annotations

import json
import logging
from sqlalchemy import inspect, text

from .database import engine
from .utils.serialization import fingerprint, utcnow

logger = logging.getLogger("qhealth.migrations")


MIGRATION_ID = "20261002_01_experiment_run_artifact"
MANIFEST_MIGRATION_ID = "20261002_02_immutable_run_manifest"
DATASET_VERSION_MIGRATION_ID = "20261002_03_dataset_versioning"
MULTI_SEED_STUDY_MIGRATION_ID = "20261003_01_multi_seed_evaluation"
EXTERNAL_VALIDATION_MIGRATION_ID = "20261003_02_external_validation"
DISTRIBUTION_SHIFT_MIGRATION_ID = "20261003_03_distribution_shift"
CALIBRATION_STUDIES_MIGRATION_ID = "20261003_04_calibration_studies"
TRAINING_EXECUTION_MIGRATION_ID = "20261003_05_training_execution_tracking"
EXPERIMENT_LIFECYCLE_MIGRATION_ID = "20261003_06_experiment_registry_lifecycle"
RESUMABLE_JOBS_MIGRATION_ID = "20261003_07_resumable_job_execution"
EVALUATION_CONTEXT_MIGRATION_ID = "20261003_08_evaluation_context_provenance"
CONTROLLED_COMPARISON_MIGRATION_ID = "20261003_09_controlled_comparison_protocol"
RESEARCH_EVIDENCE_PACKAGE_MIGRATION_ID = "20261003_10_research_evidence_packages"
DEEP_EXPERIMENT_LINEAGE_MIGRATION_ID = "20261003_11_deep_experiment_lineage"
PIPELINE_VERSION_REGISTRY_MIGRATION_ID = "20261003_12_pipeline_version_registry"
EXPERIMENT_PROTOCOLS_MIGRATION_ID = "20261003_13_experiment_protocols"
SCIENTIFIC_AUDIT_TIMELINE_MIGRATION_ID = "20261003_14_scientific_audit_timeline"
DATASET_QUALITY_SCORECARD_MIGRATION_ID = "20261003_15_advanced_dataset_quality_scorecard"
DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID = "20261003_17_dataset_version_signature_repair"
BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID = "20261003_16_restore_biomedical_subgroup_analysis"
DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID = "20261003_18_dataset_quality_scorecard_schema_repair"



def _columns(connection, table: str) -> set[str]:
    return {column["name"] for column in inspect(connection).get_columns(table)}


def _repair_dataset_quality_scorecard_schema(connection) -> None:
    """Additively repair legacy/partially-created scorecard tables."""
    additions = {
        "id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN id VARCHAR(36)",
        "schema_version": (
            "ALTER TABLE dataset_quality_scorecards ADD COLUMN schema_version "
            "VARCHAR(32) DEFAULT 'dataset_quality_scorecard_v1'"
        ),
        "dataset_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN dataset_id VARCHAR(36) REFERENCES datasets(id)",
        "dataset_version_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id)",
        "experiment_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN experiment_id VARCHAR(36) REFERENCES experiments(id)",
        "protocol_version_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN protocol_version_id VARCHAR(36) REFERENCES experiment_protocol_versions(id)",
        "pipeline_version_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id)",
        "status": "ALTER TABLE dataset_quality_scorecards ADD COLUMN status VARCHAR(24) DEFAULT 'PASS'",
        "operation_key": "ALTER TABLE dataset_quality_scorecards ADD COLUMN operation_key VARCHAR(128)",
        "assessment_fingerprint": "ALTER TABLE dataset_quality_scorecards ADD COLUMN assessment_fingerprint VARCHAR(64)",
        "configuration": "ALTER TABLE dataset_quality_scorecards ADD COLUMN configuration JSON DEFAULT '{}'",
        "summary": "ALTER TABLE dataset_quality_scorecards ADD COLUMN summary JSON DEFAULT '{}'",
        "domains": "ALTER TABLE dataset_quality_scorecards ADD COLUMN domains JSON DEFAULT '{}'",
        "schema_snapshot": "ALTER TABLE dataset_quality_scorecards ADD COLUMN schema_snapshot JSON DEFAULT '{}'",
        "limitations": "ALTER TABLE dataset_quality_scorecards ADD COLUMN limitations JSON DEFAULT '[]'",
        "provenance": "ALTER TABLE dataset_quality_scorecards ADD COLUMN provenance JSON DEFAULT '{}'",
        "artifact_id": "ALTER TABLE dataset_quality_scorecards ADD COLUMN artifact_id VARCHAR(36) REFERENCES artifacts(id)",
        "created_at": "ALTER TABLE dataset_quality_scorecards ADD COLUMN created_at DATETIME",
        "completed_at": "ALTER TABLE dataset_quality_scorecards ADD COLUMN completed_at DATETIME",
    }
    existing = _columns(connection, "dataset_quality_scorecards")
    for column, statement in additions.items():
        if column not in existing:
            connection.execute(text(statement))

    for statement in [
        "CREATE INDEX IF NOT EXISTS ix_scorecard_dataset_id ON dataset_quality_scorecards(dataset_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_dataset_version_id ON dataset_quality_scorecards(dataset_version_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_experiment_id ON dataset_quality_scorecards(experiment_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_protocol_version_id ON dataset_quality_scorecards(protocol_version_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_pipeline_version_id ON dataset_quality_scorecards(pipeline_version_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_status ON dataset_quality_scorecards(status)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_fingerprint ON dataset_quality_scorecards(assessment_fingerprint)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_operation_key ON dataset_quality_scorecards(operation_key)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_created_at ON dataset_quality_scorecards(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_dataset_version ON dataset_quality_scorecards(dataset_id, dataset_version_id)",
        "CREATE INDEX IF NOT EXISTS ix_scorecard_created_at_id ON dataset_quality_scorecards(created_at, id)",
    ]:
        connection.execute(text(statement))

    duplicate_operation_key = connection.execute(text("""
        SELECT 1
        FROM dataset_quality_scorecards
        WHERE operation_key IS NOT NULL
        GROUP BY operation_key
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate_operation_key is None:
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_dataset_quality_operation_key_compat "
            "ON dataset_quality_scorecards(operation_key) WHERE operation_key IS NOT NULL"
        ))


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

        execution_tracking_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": TRAINING_EXECUTION_MIGRATION_ID},
        ).scalar()
        if not execution_tracking_applied:
            if "name" not in _columns(connection, "experiments"):
                connection.execute(text("ALTER TABLE experiments ADD COLUMN name VARCHAR(240)"))
            if "progress" not in _columns(connection, "models"):
                connection.execute(text("ALTER TABLE models ADD COLUMN progress INTEGER"))
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_experiments_dataset_name "
                "ON experiments(dataset_id, name) WHERE name IS NOT NULL"
            ))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": TRAINING_EXECUTION_MIGRATION_ID, "applied_at": utcnow()},
            )

        experiment_lifecycle_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": EXPERIMENT_LIFECYCLE_MIGRATION_ID},
        ).scalar()
        if not experiment_lifecycle_applied:
            if "deleted_at" not in _columns(connection, "experiments"):
                connection.execute(text("ALTER TABLE experiments ADD COLUMN deleted_at DATETIME"))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_experiments_deleted_at ON experiments(deleted_at)"
            ))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": EXPERIMENT_LIFECYCLE_MIGRATION_ID, "applied_at": utcnow()},
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

        shift_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DISTRIBUTION_SHIFT_MIGRATION_ID},
        ).scalar()
        if not shift_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS distribution_shift_analyses (
                    id VARCHAR(36) PRIMARY KEY,
                    reference_dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    reference_dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    reference_content_sha256 VARCHAR(64) NOT NULL,
                    comparison_dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    comparison_dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    comparison_content_sha256 VARCHAR(64) NOT NULL,
                    model_id VARCHAR(36) REFERENCES models(id),
                    external_validation_id VARCHAR(36) REFERENCES external_validations(id),
                    parent_study_id VARCHAR(36) REFERENCES multi_seed_studies(id),
                    model_seed INTEGER,
                    status VARCHAR(24) NOT NULL DEFAULT 'created',
                    operation_key VARCHAR(128) NOT NULL UNIQUE,
                    policy_version VARCHAR(32) NOT NULL,
                    configuration JSON NOT NULL DEFAULT '{}',
                    schema_analysis JSON NOT NULL DEFAULT '{}',
                    target_analysis JSON NOT NULL DEFAULT '{}',
                    missingness_analysis JSON NOT NULL DEFAULT '{}',
                    feature_shifts JSON NOT NULL DEFAULT '[]',
                    summary JSON NOT NULL DEFAULT '{}',
                    flagged_features JSON NOT NULL DEFAULT '[]',
                    warnings JSON NOT NULL DEFAULT '[]',
                    limitations JSON NOT NULL DEFAULT '[]',
                    provenance JSON NOT NULL DEFAULT '{}',
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    failure JSON,
                    execution_time_seconds FLOAT NOT NULL DEFAULT 0.0,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_ref_dataset_id ON distribution_shift_analyses(reference_dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_comp_dataset_id ON distribution_shift_analyses(comparison_dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_model_id ON distribution_shift_analyses(model_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_ext_val_id ON distribution_shift_analyses(external_validation_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_status ON distribution_shift_analyses(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_operation_key ON distribution_shift_analyses(operation_key)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_dist_shift_created_at ON distribution_shift_analyses(created_at)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": DISTRIBUTION_SHIFT_MIGRATION_ID, "applied_at": utcnow()},
            )
        calibration_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": CALIBRATION_STUDIES_MIGRATION_ID},
        ).scalar()
        if not calibration_applied:
            connection.execute(text('''
                CREATE TABLE IF NOT EXISTS calibration_studies (
                    id VARCHAR(36) PRIMARY KEY,
                    model_id VARCHAR(36) NOT NULL REFERENCES models(id),
                    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    status VARCHAR(24) NOT NULL DEFAULT 'created',
                    operation_key VARCHAR(128) NOT NULL UNIQUE,
                    configuration JSON NOT NULL DEFAULT '{}',
                    summary JSON NOT NULL DEFAULT '{}',
                    metrics JSON NOT NULL DEFAULT '{}',
                    curves JSON NOT NULL DEFAULT '{}',
                    comparisons JSON NOT NULL DEFAULT '{}',
                    limitations JSON NOT NULL DEFAULT '[]',
                    provenance JSON NOT NULL DEFAULT '{}',
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    failure JSON,
                    execution_time_seconds FLOAT NOT NULL DEFAULT 0.0,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
            '''))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_calib_model_id ON calibration_studies(model_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_calib_dataset_id ON calibration_studies(dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_calib_status ON calibration_studies(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_calib_created_at ON calibration_studies(created_at)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": CALIBRATION_STUDIES_MIGRATION_ID, "applied_at": utcnow()},
            )


        THRESHOLD_STUDIES_MIGRATION_ID = "0010_threshold_analysis_studies"
        thresh_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": THRESHOLD_STUDIES_MIGRATION_ID},
        ).scalar()
        if not thresh_applied:
            connection.execute(text('''
                CREATE TABLE IF NOT EXISTS threshold_analysis_studies (
                    id VARCHAR(36) PRIMARY KEY,
                    model_id VARCHAR(36) NOT NULL,
                    dataset_id VARCHAR(36) NOT NULL,
                    dataset_version_id VARCHAR(36),
                    operation_key VARCHAR(128) NOT NULL,
                    configuration JSON NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'created',
                    results JSON,
                    curves JSON,
                    summary JSON,
                    limitations JSON,
                    failure JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
            '''))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_thresh_model_id ON threshold_analysis_studies(model_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_thresh_dataset_id ON threshold_analysis_studies(dataset_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_thresh_op_key ON threshold_analysis_studies(operation_key)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": THRESHOLD_STUDIES_MIGRATION_ID, "applied_at": utcnow()},
            )

        evaluation_context_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": EVALUATION_CONTEXT_MIGRATION_ID},
        ).scalar()
        if not evaluation_context_applied:
            if "provenance" not in _columns(connection, "threshold_analysis_studies"):
                connection.execute(text(
                    "ALTER TABLE threshold_analysis_studies "
                    "ADD COLUMN provenance JSON NOT NULL DEFAULT '{}'"
                ))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": EVALUATION_CONTEXT_MIGRATION_ID, "applied_at": utcnow()},
            )

        QUANTUM_DIAGNOSTICS_MIGRATION_ID = "0012_quantum_diagnostics"
        applied = connection.execute(
            text("SELECT id FROM schema_migrations WHERE id = :id"),
            {"id": QUANTUM_DIAGNOSTICS_MIGRATION_ID},
        ).fetchone()
        if not applied:
            logger.info("Applying migration 0012: quantum_diagnostics")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS quantum_diagnostic_reports (
                    id VARCHAR(36) PRIMARY KEY,
                    experiment_id VARCHAR(36) NOT NULL,
                    model_record_id VARCHAR(36) NOT NULL,
                    model_type VARCHAR(64) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'completed',
                    model_configuration JSON,
                    feature_encoding JSON,
                    circuit_structure JSON,
                    resource_profile JSON,
                    optimizer_profile JSON,
                    training_profile JSON,
                    execution_profile JSON,
                    stability_profile JSON,
                    noise_profile JSON,
                    warnings JSON,
                    limitations JSON,
                    configuration_fingerprint VARCHAR(255),
                    provenance JSON,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(experiment_id) REFERENCES experiments(id),
                    FOREIGN KEY(model_record_id) REFERENCES models(id)
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_qdiag_exp_id ON quantum_diagnostic_reports(experiment_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_qdiag_model_id ON quantum_diagnostic_reports(model_record_id)"))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": QUANTUM_DIAGNOSTICS_MIGRATION_ID, "applied_at": utcnow()},
            )

        resumable_jobs_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": RESUMABLE_JOBS_MIGRATION_ID},
        ).scalar()
        if not resumable_jobs_applied:
            job_columns = _columns(connection, "jobs")
            additions = {
                "job_type": "ALTER TABLE jobs ADD COLUMN job_type VARCHAR(48) NOT NULL DEFAULT 'training'",
                "priority": "ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0",
                "total_units": "ALTER TABLE jobs ADD COLUMN total_units INTEGER",
                "completed_units": "ALTER TABLE jobs ADD COLUMN completed_units INTEGER NOT NULL DEFAULT 0",
                "failed_units": "ALTER TABLE jobs ADD COLUMN failed_units INTEGER NOT NULL DEFAULT 0",
                "skipped_units": "ALTER TABLE jobs ADD COLUMN skipped_units INTEGER NOT NULL DEFAULT 0",
                "active_unit": "ALTER TABLE jobs ADD COLUMN active_unit VARCHAR(160)",
                "current_phase": "ALTER TABLE jobs ADD COLUMN current_phase VARCHAR(80)",
                "attempt_count": "ALTER TABLE jobs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0",
                "resume_count": "ALTER TABLE jobs ADD COLUMN resume_count INTEGER NOT NULL DEFAULT 0",
                "worker_id": "ALTER TABLE jobs ADD COLUMN worker_id VARCHAR(80)",
                "lease_id": "ALTER TABLE jobs ADD COLUMN lease_id VARCHAR(36)",
                "leased_at": "ALTER TABLE jobs ADD COLUMN leased_at DATETIME",
                "lease_expires_at": "ALTER TABLE jobs ADD COLUMN lease_expires_at DATETIME",
                "last_heartbeat_at": "ALTER TABLE jobs ADD COLUMN last_heartbeat_at DATETIME",
                "current_checkpoint_id": "ALTER TABLE jobs ADD COLUMN current_checkpoint_id VARCHAR(36) REFERENCES job_checkpoints(id)",
                "configuration_fingerprint": "ALTER TABLE jobs ADD COLUMN configuration_fingerprint VARCHAR(64)",
                "input_fingerprint": "ALTER TABLE jobs ADD COLUMN input_fingerprint VARCHAR(64)",
                "output_artifact_id": "ALTER TABLE jobs ADD COLUMN output_artifact_id VARCHAR(36) REFERENCES artifacts(id)",
                "failure_category": "ALTER TABLE jobs ADD COLUMN failure_category VARCHAR(48)",
                "error_code": "ALTER TABLE jobs ADD COLUMN error_code VARCHAR(80)",
                "error_message": "ALTER TABLE jobs ADD COLUMN error_message VARCHAR(240)",
                "requested_at": "ALTER TABLE jobs ADD COLUMN requested_at DATETIME",
                "started_at": "ALTER TABLE jobs ADD COLUMN started_at DATETIME",
                "completed_at": "ALTER TABLE jobs ADD COLUMN completed_at DATETIME",
                "cancelled_at": "ALTER TABLE jobs ADD COLUMN cancelled_at DATETIME",
            }
            for column, statement in additions.items():
                if column not in job_columns:
                    connection.execute(text(statement))
            connection.execute(text("UPDATE jobs SET requested_at = COALESCE(requested_at, created_at)"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS job_checkpoints (
                    id VARCHAR(36) PRIMARY KEY, job_id VARCHAR(36) NOT NULL REFERENCES jobs(id),
                    sequence_number INTEGER NOT NULL, checkpoint_type VARCHAR(32) NOT NULL DEFAULT 'unit_completion',
                    status VARCHAR(24) NOT NULL DEFAULT 'pending', logical_unit VARCHAR(160),
                    completed_units INTEGER NOT NULL DEFAULT 0, checkpoint_state JSON NOT NULL DEFAULT '{}',
                    state_fingerprint VARCHAR(64) NOT NULL, input_fingerprint VARCHAR(64),
                    configuration_fingerprint VARCHAR(64), artifact_references JSON NOT NULL DEFAULT '[]',
                    created_at DATETIME NOT NULL, validated_at DATETIME, invalidated_at DATETIME,
                    CONSTRAINT uq_job_checkpoints_sequence UNIQUE(job_id, sequence_number))
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS job_execution_units (
                    id VARCHAR(36) PRIMARY KEY, job_id VARCHAR(36) NOT NULL REFERENCES jobs(id),
                    logical_key VARCHAR(200) NOT NULL, phase VARCHAR(80), unit_index INTEGER,
                    status VARCHAR(24) NOT NULL DEFAULT 'running', result_reference VARCHAR(320),
                    result_fingerprint VARCHAR(64), started_at DATETIME NOT NULL, completed_at DATETIME,
                    CONSTRAINT uq_job_execution_units_logical_key UNIQUE(job_id, logical_key))
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS job_events (
                    id VARCHAR(36) PRIMARY KEY, job_id VARCHAR(36) NOT NULL REFERENCES jobs(id),
                    event_type VARCHAR(48) NOT NULL, from_status VARCHAR(24), to_status VARCHAR(24),
                    checkpoint_id VARCHAR(36) REFERENCES job_checkpoints(id), worker_id VARCHAR(80),
                    details JSON NOT NULL DEFAULT '{}', created_at DATETIME NOT NULL)
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_jobs_job_type ON jobs(job_type)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_worker_id ON jobs(worker_id)",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_lease_id ON jobs(lease_id) WHERE lease_id IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS ix_jobs_lease_expires_at ON jobs(lease_expires_at)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_last_heartbeat_at ON jobs(last_heartbeat_at)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_current_checkpoint_id ON jobs(current_checkpoint_id)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_configuration_fingerprint ON jobs(configuration_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_input_fingerprint ON jobs(input_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_jobs_failure_category ON jobs(failure_category)",
                "CREATE INDEX IF NOT EXISTS ix_job_checkpoints_job_id ON job_checkpoints(job_id)",
                "CREATE INDEX IF NOT EXISTS ix_job_checkpoints_status ON job_checkpoints(status)",
                "CREATE INDEX IF NOT EXISTS ix_job_execution_units_job_id ON job_execution_units(job_id)",
                "CREATE INDEX IF NOT EXISTS ix_job_execution_units_status ON job_execution_units(status)",
                "CREATE INDEX IF NOT EXISTS ix_job_events_job_id ON job_events(job_id)",
                "CREATE INDEX IF NOT EXISTS ix_job_events_event_type ON job_events(event_type)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": RESUMABLE_JOBS_MIGRATION_ID, "applied_at": utcnow()},
            )

        controlled_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": CONTROLLED_COMPARISON_MIGRATION_ID},
        ).scalar()
        if not controlled_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS controlled_comparison_protocols (
                    id VARCHAR(36) PRIMARY KEY,
                    experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id),
                    schema_version VARCHAR(48) NOT NULL,
                    status VARCHAR(40) NOT NULL,
                    operation_key VARCHAR(160) NOT NULL UNIQUE,
                    configuration_fingerprint VARCHAR(64) NOT NULL,
                    protocol_fingerprint VARCHAR(64) NOT NULL,
                    classical_model_ids JSON NOT NULL DEFAULT '[]',
                    quantum_model_ids JSON NOT NULL DEFAULT '[]',
                    comparison_pairs JSON NOT NULL DEFAULT '[]',
                    control_summary JSON NOT NULL DEFAULT '{}',
                    provenance JSON NOT NULL DEFAULT '{}',
                    limitations JSON NOT NULL DEFAULT '[]',
                    warnings JSON NOT NULL DEFAULT '[]',
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    created_at DATETIME NOT NULL
                )
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_controlled_protocol_experiment_id ON controlled_comparison_protocols(experiment_id)",
                "CREATE INDEX IF NOT EXISTS ix_controlled_protocol_status ON controlled_comparison_protocols(status)",
                "CREATE INDEX IF NOT EXISTS ix_controlled_protocol_operation_key ON controlled_comparison_protocols(operation_key)",
                "CREATE INDEX IF NOT EXISTS ix_controlled_protocol_fingerprint ON controlled_comparison_protocols(protocol_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_controlled_protocol_created_at ON controlled_comparison_protocols(created_at)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": CONTROLLED_COMPARISON_MIGRATION_ID, "applied_at": utcnow()},
            )

        evidence_package_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": RESEARCH_EVIDENCE_PACKAGE_MIGRATION_ID},
        ).scalar()
        if not evidence_package_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS research_evidence_packages (
                    id VARCHAR(36) PRIMARY KEY,
                    experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id),
                    schema_version VARCHAR(48) NOT NULL,
                    status VARCHAR(24) NOT NULL,
                    package_fingerprint VARCHAR(64) NOT NULL,
                    configuration_fingerprint VARCHAR(64),
                    source_context_type VARCHAR(40) NOT NULL,
                    evidence_inventory JSON NOT NULL DEFAULT '{}',
                    provenance JSON NOT NULL DEFAULT '{}',
                    limitations JSON NOT NULL DEFAULT '[]',
                    evidence_gaps JSON NOT NULL DEFAULT '[]',
                    manifest JSON NOT NULL DEFAULT '{}',
                    artifact_id VARCHAR(36) NOT NULL REFERENCES artifacts(id),
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_research_evidence_package_snapshot
                        UNIQUE(experiment_id, package_fingerprint)
                )
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_experiment_id ON research_evidence_packages(experiment_id)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_fingerprint ON research_evidence_packages(package_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_status ON research_evidence_packages(status)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_configuration_fingerprint ON research_evidence_packages(configuration_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_source_context_type ON research_evidence_packages(source_context_type)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_artifact_id ON research_evidence_packages(artifact_id)",
                "CREATE INDEX IF NOT EXISTS ix_research_evidence_packages_created_at ON research_evidence_packages(created_at)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": RESEARCH_EVIDENCE_PACKAGE_MIGRATION_ID, "applied_at": utcnow()},
            )

        lineage_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DEEP_EXPERIMENT_LINEAGE_MIGRATION_ID},
        ).scalar()
        if not lineage_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS lineage_nodes (
                    id VARCHAR(36) PRIMARY KEY,
                    object_type VARCHAR(48) NOT NULL,
                    object_id VARCHAR(64) NOT NULL,
                    schema_version VARCHAR(40) NOT NULL,
                    reference_fingerprint VARCHAR(64),
                    reference_metadata JSON NOT NULL DEFAULT '{}',
                    recorded_at DATETIME NOT NULL,
                    CONSTRAINT uq_lineage_node_object UNIQUE(object_type, object_id)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS lineage_edges (
                    id VARCHAR(36) PRIMARY KEY,
                    source_node_id VARCHAR(36) NOT NULL REFERENCES lineage_nodes(id),
                    target_node_id VARCHAR(36) NOT NULL REFERENCES lineage_nodes(id),
                    relationship_type VARCHAR(48) NOT NULL,
                    schema_version VARCHAR(40) NOT NULL,
                    relationship_fingerprint VARCHAR(64) NOT NULL,
                    relationship_metadata JSON NOT NULL DEFAULT '{}',
                    immutable BOOLEAN NOT NULL DEFAULT 1,
                    recorded_at DATETIME NOT NULL,
                    CONSTRAINT uq_lineage_edge_relationship
                        UNIQUE(source_node_id, target_node_id, relationship_type)
                )
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_lineage_nodes_object_type ON lineage_nodes(object_type)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_nodes_object_id ON lineage_nodes(object_id)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_nodes_reference_fingerprint ON lineage_nodes(reference_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_nodes_recorded_at ON lineage_nodes(recorded_at)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_edges_source_node_id ON lineage_edges(source_node_id)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_edges_target_node_id ON lineage_edges(target_node_id)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_edges_relationship_type ON lineage_edges(relationship_type)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_edges_relationship_fingerprint ON lineage_edges(relationship_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_lineage_edges_recorded_at ON lineage_edges(recorded_at)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": DEEP_EXPERIMENT_LINEAGE_MIGRATION_ID, "applied_at": utcnow()},
            )

        pipeline_registry_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": PIPELINE_VERSION_REGISTRY_MIGRATION_ID},
        ).scalar()
        if not pipeline_registry_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_definitions (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    source_context VARCHAR(48),
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_pipeline_definition_name UNIQUE(name)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_versions (
                    id VARCHAR(36) PRIMARY KEY,
                    pipeline_definition_id VARCHAR(36) NOT NULL REFERENCES pipeline_definitions(id),
                    version_number INTEGER NOT NULL,
                    version_label VARCHAR(24) NOT NULL,
                    schema_version VARCHAR(48) NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT',
                    description TEXT NOT NULL DEFAULT '',
                    definition_fingerprint VARCHAR(64) NOT NULL,
                    canonical_definition JSON NOT NULL,
                    parent_pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id),
                    controlled_comparison_protocol_id VARCHAR(36) REFERENCES controlled_comparison_protocols(id),
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    source_context VARCHAR(48),
                    published_at DATETIME,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_pipeline_version_number UNIQUE(pipeline_definition_id, version_number),
                    CONSTRAINT uq_pipeline_version_fingerprint UNIQUE(definition_fingerprint)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_stages (
                    id VARCHAR(36) PRIMARY KEY,
                    pipeline_version_id VARCHAR(36) NOT NULL REFERENCES pipeline_versions(id),
                    stage_order INTEGER NOT NULL,
                    stage_type VARCHAR(48) NOT NULL,
                    stage_name VARCHAR(120) NOT NULL,
                    configuration JSON NOT NULL,
                    component_version VARCHAR(64),
                    stage_fingerprint VARCHAR(64) NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_pipeline_stage_order UNIQUE(pipeline_version_id, stage_order)
                )
            """))
            if "pipeline_version_id" not in _columns(connection, "experiments"):
                connection.execute(text(
                    "ALTER TABLE experiments ADD COLUMN pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id)"
                ))
            if "pipeline_version_id" not in _columns(connection, "runs"):
                connection.execute(text(
                    "ALTER TABLE runs ADD COLUMN pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id)"
                ))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_pipeline_definitions_name ON pipeline_definitions(name)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_definitions_created_at ON pipeline_definitions(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_pipeline_definition_id ON pipeline_versions(pipeline_definition_id)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_status ON pipeline_versions(status)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_definition_fingerprint ON pipeline_versions(definition_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_parent_pipeline_version_id ON pipeline_versions(parent_pipeline_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_controlled_comparison_protocol_id ON pipeline_versions(controlled_comparison_protocol_id)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_artifact_id ON pipeline_versions(artifact_id)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_versions_created_at ON pipeline_versions(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_stages_pipeline_version_id ON pipeline_stages(pipeline_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_stages_stage_type ON pipeline_stages(stage_type)",
                "CREATE INDEX IF NOT EXISTS ix_pipeline_stages_stage_fingerprint ON pipeline_stages(stage_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_experiments_pipeline_version_id ON experiments(pipeline_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_runs_pipeline_version_id ON runs(pipeline_version_id)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": PIPELINE_VERSION_REGISTRY_MIGRATION_ID, "applied_at": utcnow()},
            )

        protocols_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": EXPERIMENT_PROTOCOLS_MIGRATION_ID},
        ).scalar()
        if not protocols_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS protocol_templates (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    version VARCHAR(24) NOT NULL DEFAULT 'v1',
                    status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
                    task_type VARCHAR(64) NOT NULL DEFAULT 'binary_classification',
                    canonical_definition JSON NOT NULL,
                    parameters_schema JSON NOT NULL DEFAULT '{}',
                    template_fingerprint VARCHAR(64) NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_protocol_template_name UNIQUE(name)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS experiment_protocols (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    template_id VARCHAR(36) REFERENCES protocol_templates(id),
                    source_context VARCHAR(48),
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_experiment_protocol_name UNIQUE(name)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS experiment_protocol_versions (
                    id VARCHAR(36) PRIMARY KEY,
                    protocol_id VARCHAR(36) NOT NULL REFERENCES experiment_protocols(id),
                    version_number INTEGER NOT NULL,
                    version_label VARCHAR(24) NOT NULL,
                    schema_version VARCHAR(48) NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'DRAFT',
                    description TEXT NOT NULL DEFAULT '',
                    definition_fingerprint VARCHAR(64) NOT NULL,
                    canonical_definition JSON NOT NULL,
                    parent_protocol_version_id VARCHAR(36) REFERENCES experiment_protocol_versions(id),
                    template_id VARCHAR(36) REFERENCES protocol_templates(id),
                    pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id),
                    controlled_comparison_protocol_id VARCHAR(36) REFERENCES controlled_comparison_protocols(id),
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    source_context VARCHAR(48),
                    published_at DATETIME,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_experiment_protocol_version_number UNIQUE(protocol_id, version_number),
                    CONSTRAINT uq_experiment_protocol_version_fingerprint UNIQUE(definition_fingerprint)
                )
            """))
            if "protocol_version_id" not in _columns(connection, "experiments"):
                connection.execute(text(
                    "ALTER TABLE experiments ADD COLUMN protocol_version_id VARCHAR(36) REFERENCES experiment_protocol_versions(id)"
                ))
            if "protocol_fingerprint" not in _columns(connection, "experiments"):
                connection.execute(text(
                    "ALTER TABLE experiments ADD COLUMN protocol_fingerprint VARCHAR(64)"
                ))
            if "protocol_version_id" not in _columns(connection, "runs"):
                connection.execute(text(
                    "ALTER TABLE runs ADD COLUMN protocol_version_id VARCHAR(36) REFERENCES experiment_protocol_versions(id)"
                ))
            if "protocol_fingerprint" not in _columns(connection, "runs"):
                connection.execute(text(
                    "ALTER TABLE runs ADD COLUMN protocol_fingerprint VARCHAR(64)"
                ))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_protocol_templates_name ON protocol_templates(name)",
                "CREATE INDEX IF NOT EXISTS ix_protocol_templates_status ON protocol_templates(status)",
                "CREATE INDEX IF NOT EXISTS ix_protocol_templates_fingerprint ON protocol_templates(template_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_protocol_templates_created_at ON protocol_templates(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_experiment_protocols_name ON experiment_protocols(name)",
                "CREATE INDEX IF NOT EXISTS ix_experiment_protocols_template_id ON experiment_protocols(template_id)",
                "CREATE INDEX IF NOT EXISTS ix_experiment_protocols_created_at ON experiment_protocols(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_protocol_id ON experiment_protocol_versions(protocol_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_status ON experiment_protocol_versions(status)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_fingerprint ON experiment_protocol_versions(definition_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_parent_id ON experiment_protocol_versions(parent_protocol_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_template_id ON experiment_protocol_versions(template_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_pipeline_ver_id ON experiment_protocol_versions(pipeline_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_controlled_id ON experiment_protocol_versions(controlled_comparison_protocol_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_artifact_id ON experiment_protocol_versions(artifact_id)",
                "CREATE INDEX IF NOT EXISTS ix_exp_proto_ver_created_at ON experiment_protocol_versions(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_experiments_protocol_version_id ON experiments(protocol_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_experiments_protocol_fingerprint ON experiments(protocol_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_runs_protocol_version_id ON runs(protocol_version_id)",
                "CREATE INDEX IF NOT EXISTS ix_runs_protocol_fingerprint ON runs(protocol_fingerprint)",
            ]:
                connection.execute(text(statement))

            # Seed default templates
            from .protocols.templates import BUILTIN_TEMPLATES, _template_id
            from .protocols.service import canonicalize_definition, definition_fingerprint
            for tpl in BUILTIN_TEMPLATES:
                canonical = canonicalize_definition(tpl["definition"])
                t_fingerprint = definition_fingerprint(canonical)
                t_id = _template_id(tpl["name"])
                connection.execute(
                    text("""
                        INSERT OR IGNORE INTO protocol_templates (
                            id, name, description, version, status, task_type,
                            canonical_definition, parameters_schema, template_fingerprint, created_at
                        ) VALUES (
                            :id, :name, :description, :version, :status, :task_type,
                            :canonical_definition, :parameters_schema, :template_fingerprint, :created_at
                        )
                    """),
                    {
                        "id": t_id,
                        "name": tpl["name"],
                        "description": tpl["description"],
                        "version": tpl["version"],
                        "status": "ACTIVE",
                        "task_type": tpl["task_type"],
                        "canonical_definition": json.dumps(canonical),
                        "parameters_schema": json.dumps(tpl["parameters_schema"]),
                        "template_fingerprint": t_fingerprint,
                        "created_at": utcnow(),
                    },
                )

            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": EXPERIMENT_PROTOCOLS_MIGRATION_ID, "applied_at": utcnow()},
            )

        audit_timeline_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": SCIENTIFIC_AUDIT_TIMELINE_MIGRATION_ID},
        ).scalar()
        if not audit_timeline_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS scientific_audit_events (
                    id VARCHAR(36) PRIMARY KEY,
                    schema_version VARCHAR(32) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    event_category VARCHAR(32) NOT NULL,
                    occurred_at DATETIME NOT NULL,
                    recorded_at DATETIME NOT NULL,
                    actor_type VARCHAR(24) NOT NULL,
                    actor_reference VARCHAR(120),
                    source_component VARCHAR(64) NOT NULL,
                    operation_key VARCHAR(240),
                    object_type VARCHAR(48) NOT NULL,
                    object_id VARCHAR(64) NOT NULL,
                    parent_object_type VARCHAR(48),
                    parent_object_id VARCHAR(64),
                    before_fingerprint VARCHAR(64),
                    after_fingerprint VARCHAR(64),
                    previous_event_fingerprint VARCHAR(64),
                    event_fingerprint VARCHAR(64) NOT NULL,
                    metadata JSON NOT NULL,
                    CONSTRAINT uq_audit_operation_event UNIQUE(operation_key, event_type)
                )
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON scientific_audit_events(event_type)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_event_category ON scientific_audit_events(event_category)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_occurred_at ON scientific_audit_events(occurred_at)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_recorded_at ON scientific_audit_events(recorded_at)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_object_type_id ON scientific_audit_events(object_type, object_id)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_parent_object_id ON scientific_audit_events(parent_object_type, parent_object_id)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_occurred_at_id ON scientific_audit_events(occurred_at, id)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_source_component ON scientific_audit_events(source_component)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_operation_key ON scientific_audit_events(operation_key)",
                "CREATE INDEX IF NOT EXISTS ix_audit_events_event_fingerprint ON scientific_audit_events(event_fingerprint)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": SCIENTIFIC_AUDIT_TIMELINE_MIGRATION_ID, "applied_at": utcnow()},
            )

        subgroup_analysis_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID},
        ).scalar()
        if not subgroup_analysis_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS subgroup_analysis_studies (
                    id VARCHAR(36) PRIMARY KEY,
                    schema_version VARCHAR(32) NOT NULL,
                    experiment_id VARCHAR(36) NOT NULL REFERENCES experiments(id),
                    model_id VARCHAR(36) NOT NULL REFERENCES models(id),
                    run_id VARCHAR(36) REFERENCES runs(id),
                    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    status VARCHAR(24) NOT NULL,
                    operation_key VARCHAR(128) NOT NULL UNIQUE,
                    definition_fingerprint VARCHAR(64) NOT NULL,
                    subgroup_field VARCHAR(100) NOT NULL,
                    configuration JSON NOT NULL,
                    overall_population JSON NOT NULL,
                    subgroups_results JSON NOT NULL,
                    comparisons JSON NOT NULL,
                    limitations JSON NOT NULL,
                    provenance JSON NOT NULL,
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    failure JSON,
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME
                )
            """))
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_experiment_id ON subgroup_analysis_studies(experiment_id)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_model_id ON subgroup_analysis_studies(model_id)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_dataset_id ON subgroup_analysis_studies(dataset_id)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_field ON subgroup_analysis_studies(subgroup_field)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_operation_key ON subgroup_analysis_studies(operation_key)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_fingerprint ON subgroup_analysis_studies(definition_fingerprint)",
                "CREATE INDEX IF NOT EXISTS ix_subgroup_studies_created_at ON subgroup_analysis_studies(created_at)",
            ]:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID, "applied_at": utcnow()},
            )


        dataset_version_signature_repair_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID},
        ).scalar()
        if not dataset_version_signature_repair_applied:
            dataset_version_columns = _columns(connection, "dataset_versions")
            if "version_signature" not in dataset_version_columns:
                connection.execute(
                    text("ALTER TABLE dataset_versions ADD COLUMN version_signature VARCHAR(64)")
                )

            legacy_versions = connection.execute(text("""
                SELECT id, dataset_id, content_sha256, schema_fingerprint,
                       target, positive_label, negative_label
                FROM dataset_versions
                WHERE version_signature IS NULL
            """)).mappings().all()
            for row in legacy_versions:
                signature = fingerprint({
                    "content_sha256": row["content_sha256"],
                    "schema_fingerprint": row["schema_fingerprint"],
                    "target": row["target"],
                    "positive_label": str(row["positive_label"]),
                    "negative_label": str(row["negative_label"]),
                })
                connection.execute(
                    text("UPDATE dataset_versions SET version_signature = :signature WHERE id = :id"),
                    {"signature": signature, "id": row["id"]},
                )

            duplicate_signature = connection.execute(text("""
                SELECT 1
                FROM dataset_versions
                GROUP BY dataset_id, version_signature
                HAVING COUNT(*) > 1
                LIMIT 1
            """)).first()
            if duplicate_signature is None:
                connection.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_dataset_versions_signature_compat "
                    "ON dataset_versions(dataset_id, version_signature)"
                ))
            else:
                # Preserve historical rows if duplicate signatures already exist;
                # application-level idempotency still resolves exact content before insert.
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_dataset_versions_version_signature "
                    "ON dataset_versions(dataset_id, version_signature)"
                ))

            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID, "applied_at": utcnow()},
            )
        scorecard_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DATASET_QUALITY_SCORECARD_MIGRATION_ID},
        ).scalar()
        if not scorecard_applied:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS dataset_quality_scorecards (
                    id VARCHAR(36) PRIMARY KEY,
                    schema_version VARCHAR(32) NOT NULL,
                    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id),
                    dataset_version_id VARCHAR(36) REFERENCES dataset_versions(id),
                    experiment_id VARCHAR(36) REFERENCES experiments(id),
                    protocol_version_id VARCHAR(36) REFERENCES experiment_protocol_versions(id),
                    pipeline_version_id VARCHAR(36) REFERENCES pipeline_versions(id),
                    status VARCHAR(24) NOT NULL DEFAULT 'PASS',
                    operation_key VARCHAR(128) NOT NULL,
                    assessment_fingerprint VARCHAR(64) NOT NULL,
                    configuration JSON NOT NULL,
                    summary JSON NOT NULL,
                    domains JSON NOT NULL,
                    schema_snapshot JSON NOT NULL,
                    limitations JSON NOT NULL,
                    provenance JSON NOT NULL,
                    artifact_id VARCHAR(36) REFERENCES artifacts(id),
                    created_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    CONSTRAINT uq_dataset_quality_operation_key UNIQUE(operation_key)
                )
            """))
            _repair_dataset_quality_scorecard_schema(connection)
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": DATASET_QUALITY_SCORECARD_MIGRATION_ID, "applied_at": utcnow()},
            )
        scorecard_repair_applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :id"),
            {"id": DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID},
        ).scalar()
        if not scorecard_repair_applied:
            _repair_dataset_quality_scorecard_schema(connection)
            connection.execute(
                text("INSERT INTO schema_migrations (id, applied_at) VALUES (:id, :applied_at)"),
                {"id": DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID, "applied_at": utcnow()},
            )
