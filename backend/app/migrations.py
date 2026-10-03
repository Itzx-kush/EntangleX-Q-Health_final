"""Small, explicit SQLite migrations for the existing local research registry.

The project historically initialized tables with ``create_all``.  Migrations
therefore remain deliberately dependency-free and additive: they never drop,
rename, or rewrite historical rows.
"""

from __future__ import annotations

import logging
from sqlalchemy import inspect, text

from .database import engine
from .utils.serialization import utcnow

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
