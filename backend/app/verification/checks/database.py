"""Database and migration verification.

The checks build and migrate an isolated SQLite database, confirm that every
declared ORM table materializes, and prove that re-running the additive
migrations on an existing database neither loses historical rows nor reports a
migration twice.  Real production data is never used.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import inspect, text

from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check

REQUIRED_SCIENTIFIC_TABLES = (
    "artifacts",
    "datasets",
    "dataset_versions",
    "experiments",
    "runs",
    "models",
    "pipeline_definitions",
    "pipeline_versions",
    "pipeline_stages",
    "experiment_protocol_versions",
    "protocol_templates",
    "research_evidence_packages",
    "lineage_nodes",
    "lineage_edges",
    "scientific_audit_events",
    "subgroup_analysis_studies",
    "dataset_quality_scorecards",
    "controlled_comparison_protocols",
    "quantum_diagnostic_reports",
    "multi_seed_studies",
    "external_validations",
    "distribution_shift_analyses",
    "calibration_studies",
    "threshold_analysis_studies",
    "ablation_studies",
)


def _sqlite_tables() -> set[str]:
    from app.database import engine

    return set(inspect(engine).get_table_names())


def _orm_tables() -> set[str]:
    from app.database import Base
    from app.storage import entities  # noqa: F401  (registers every mapped table)

    return set(Base.metadata.tables)


@check(
    check_id="database_schema_contract",
    name="Database schema contract",
    category=CheckCategory.DATABASE_MIGRATION,
    description="Creates the schema on a fresh isolated database and confirms every ORM table, scientific table and migration record exists.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def database_schema_contract() -> CheckResult:
    initialize_database()
    declared = _orm_tables()
    materialized = _sqlite_tables()
    missing_orm = sorted(declared - materialized)
    missing_scientific = sorted(set(REQUIRED_SCIENTIFIC_TABLES) - materialized)
    if missing_orm or missing_scientific:
        return CheckResult(
            check_id="database_schema_contract",
            category=CheckCategory.DATABASE_MIGRATION.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=(
                "The initialized database is missing declared tables "
                f"(orm={missing_orm[:5]}, scientific={missing_scientific[:5]})."
            ),
            evidence={
                "missing_orm_tables": missing_orm,
                "missing_scientific_tables": missing_scientific,
                "table_count": len(materialized),
            },
            failure_category=FailureCategory.MIGRATION_FAILURE,
            expected="every ORM-declared and required scientific table exists after initialization",
            observed=f"{len(missing_orm)} ORM table(s) and {len(missing_scientific)} scientific table(s) missing",
        )

    from app.database import engine

    inspector = inspect(engine)
    column_mismatches: list[dict] = []
    for table_name in sorted(declared):
        sqlite_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in Base_columns(table_name):
            if column not in sqlite_columns:
                column_mismatches.append({"table": table_name, "missing_column": column})
    if column_mismatches:
        return CheckResult(
            check_id="database_schema_contract",
            category=CheckCategory.DATABASE_MIGRATION.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="Materialized tables do not expose every column declared by the ORM models.",
            evidence={"mismatches": column_mismatches[:20]},
            failure_category=FailureCategory.MIGRATION_FAILURE,
            expected="SQLite columns match ORM column declarations",
            observed=f"{len(column_mismatches)} column mismatch(es)",
        )

    with session() as scope:
        migration_ids = [row for row in scope.execute(text("SELECT id FROM schema_migrations")).scalars()]
        template_count = scope.execute(text("SELECT COUNT(*) FROM protocol_templates")).scalar_one()
    duplicates = sorted({item for item in migration_ids if migration_ids.count(item) > 1})
    if duplicates:
        return CheckResult(
            check_id="database_schema_contract",
            category=CheckCategory.DATABASE_MIGRATION.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message=f"schema_migrations contains duplicate identifiers: {duplicates}.",
            evidence={"duplicates": duplicates},
            failure_category=FailureCategory.MIGRATION_FAILURE,
            expected="each migration identifier recorded exactly once",
            observed=f"duplicates: {duplicates}",
        )
    return CheckResult(
        check_id="database_schema_contract",
        category=CheckCategory.DATABASE_MIGRATION.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Fresh isolated database materializes every declared table, column and migration record.",
        evidence={
            "table_count": len(materialized),
            "orm_table_count": len(declared),
            "migration_count": len(migration_ids),
            "protocol_template_count": template_count,
        },
    )


def Base_columns(table_name: str) -> list[str]:
    from app.database import Base

    return [column.name for column in Base.metadata.tables[table_name].columns]


@check(
    check_id="database_migration_upgrade_path",
    name="Migration upgrade path",
    category=CheckCategory.DATABASE_MIGRATION,
    description="Re-applies the additive migrations on an existing database that already contains legacy rows and confirms nothing is lost or re-applied.",
    severity=Severity.REQUIRED,
    profiles=(FULL_PROFILE,),
    timeout_seconds=240.0,
)
def database_migration_upgrade_path() -> CheckResult:
    from app.database import engine
    from app.migrations import apply_migrations
    from app.storage.entities import Dataset, Experiment, ModelRecord, Run
    from app.utils.serialization import utcnow

    initialize_database()
    dataset_id, experiment_id, run_id, model_id = (str(uuid4()) for _ in range(4))
    legacy_config = {"dataset_id": dataset_id, "models": ["logistic_regression"], "seed": 19, "legacy": True}
    with session() as scope:
        scope.add(
            Dataset(
                id=dataset_id,
                name="Legacy synthetic dataset",
                filename="legacy.csv",
                sha256="0" * 64,
                provenance={"synthetic": True, "legacy": True},
                quality={},
                created_at=utcnow(),
            )
        )
        scope.flush()
        scope.add(
            Experiment(
                id=experiment_id,
                name="Legacy synthetic experiment",
                dataset_id=dataset_id,
                status="completed",
                config=legacy_config,
                summary={"legacy": True},
            )
        )
        scope.flush()
        scope.add(
            Run(
                id=run_id,
                experiment_id=experiment_id,
                dataset_id=dataset_id,
                status="completed",
                operation_key=f"legacy:{run_id}",
                config=legacy_config,
                execution_metadata={},
                reproducibility_metadata={},
                result_summary={},
                configuration_fingerprint="0" * 64,
                reproducibility_status="legacy_unresolved",
            )
        )
        scope.flush()
        scope.add(
            ModelRecord(
                id=model_id,
                experiment_id=experiment_id,
                run_id=run_id,
                dataset_id=dataset_id,
                model_type="logistic_regression",
                status="ready",
                artifact_sha256="0" * 64,
                details={},
                metrics={},
            )
        )
        before_migrations = scope.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar_one()

    apply_migrations()
    apply_migrations()

    with session() as scope:
        after_migrations = scope.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar_one()
        legacy = scope.get(Experiment, experiment_id)
        legacy_run = scope.get(Run, run_id)
        legacy_model = scope.get(ModelRecord, model_id)
        pipeline_columns = {
            column["name"] for column in inspect(engine).get_columns("experiments")
        }

    problems: list[str] = []
    if after_migrations != before_migrations:
        problems.append(
            f"schema_migrations changed on re-application ({before_migrations} -> {after_migrations})"
        )
    if legacy is None or legacy.config != legacy_config or legacy.summary != {"legacy": True}:
        problems.append("the legacy experiment row was modified or lost")
    if legacy_run is None or legacy_model is None:
        problems.append("legacy run or model rows were lost")
    if legacy is not None and legacy.pipeline_version_id is not None:
        problems.append("a pipeline version was fabricated for a legacy experiment")
    if legacy is not None and legacy.protocol_version_id is not None:
        problems.append("a protocol version was fabricated for a legacy experiment")
    if not {"pipeline_version_id", "protocol_version_id"}.issubset(pipeline_columns):
        problems.append("additive experiment columns are missing after migration")
    if problems:
        return CheckResult(
            check_id="database_migration_upgrade_path",
            category=CheckCategory.DATABASE_MIGRATION.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems, "migration_count": after_migrations},
            failure_category=FailureCategory.MIGRATION_FAILURE,
            expected="re-applying additive migrations preserves legacy rows and records no new migration",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="database_migration_upgrade_path",
        category=CheckCategory.DATABASE_MIGRATION.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Migrations are idempotent on an existing database and preserve legacy rows without fabricating provenance.",
        evidence={
            "migration_count": after_migrations,
            "legacy_experiment_preserved": True,
            "fabricated_references": False,
        },
    )
