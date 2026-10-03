from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.database import Base, engine
from app.dataset_versions.service import version_signature
from app import migrations
from app.migrations import (
    BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID,
    DATASET_QUALITY_SCORECARD_MIGRATION_ID,
    DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID,
    DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID,
    _repair_dataset_quality_scorecard_schema,
    _repair_dataset_version_signatures,
)


def _legacy_versions_table(connection) -> None:
    connection.execute(text("""
        CREATE TABLE dataset_versions (
            id VARCHAR(36) PRIMARY KEY,
            dataset_id VARCHAR(36) NOT NULL,
            version_number INTEGER NOT NULL,
            version_label VARCHAR(24) NOT NULL,
            content_sha256 VARCHAR(64) NOT NULL,
            schema_fingerprint VARCHAR(64) NOT NULL,
            target VARCHAR(100) NOT NULL,
            positive_label VARCHAR(64) NOT NULL,
            negative_label VARCHAR(64) NOT NULL,
            target_type VARCHAR(40) NOT NULL DEFAULT 'binary_classification',
            class_distribution JSON NOT NULL DEFAULT '{}',
            source_metadata JSON NOT NULL DEFAULT '{}',
            provenance JSON NOT NULL DEFAULT '{}',
            quality_summary JSON NOT NULL DEFAULT '{}',
            storage_reference VARCHAR(320) NOT NULL DEFAULT '',
            status VARCHAR(24) NOT NULL DEFAULT 'ready',
            immutable BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME
        )
    """))


def test_legacy_dataset_version_signature_repair_is_canonical_and_idempotent(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-versions.sqlite3'}")
    with legacy_engine.begin() as connection:
        _legacy_versions_table(connection)
        connection.execute(text("""
            INSERT INTO dataset_versions
                (id, dataset_id, version_number, version_label, content_sha256, schema_fingerprint,
                 target, positive_label, negative_label)
            VALUES
                ('version-1', 'dataset-1', 1, 'v1', 'content-1', 'schema-1',
                 'target', 'positive', 'negative')
        """))
        _repair_dataset_version_signatures(connection)
        _repair_dataset_version_signatures(connection)

    inspector = inspect(legacy_engine)
    assert 'version_signature' in {column['name'] for column in inspector.get_columns('dataset_versions')}
    assert 'uq_dataset_versions_signature_compat' in {index['name'] for index in inspector.get_indexes('dataset_versions')}
    with legacy_engine.connect() as connection:
        row = connection.execute(text(
            "SELECT id, version_signature FROM dataset_versions WHERE id = 'version-1'"
        )).one()
    assert row.version_signature == version_signature('content-1', 'schema-1', 'target', 'positive', 'negative')


def test_duplicate_legacy_signatures_get_non_unique_compatibility_index(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'duplicate-versions.sqlite3'}")
    with legacy_engine.begin() as connection:
        _legacy_versions_table(connection)
        for version_id in ('version-1', 'version-2'):
            connection.execute(text("""
                INSERT INTO dataset_versions
                    (id, dataset_id, version_number, version_label, content_sha256, schema_fingerprint,
                     target, positive_label, negative_label)
                VALUES
                    (:id, 'dataset-1', 1, 'v1', 'content-1', 'schema-1',
                     'target', 'positive', 'negative')
            """), {'id': version_id})
        _repair_dataset_version_signatures(connection)

    indexes = {index['name']: index for index in inspect(legacy_engine).get_indexes('dataset_versions')}
    assert 'uq_dataset_versions_signature_compat' not in indexes
    assert 'ix_dataset_versions_version_signature' in indexes


def test_duplicate_legacy_scorecard_operation_keys_get_non_unique_index(tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'duplicate-scorecards.sqlite3'}")
    with legacy_engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE dataset_quality_scorecards (
                id VARCHAR(36) PRIMARY KEY,
                dataset_id VARCHAR(36),
                operation_key VARCHAR(128),
                summary JSON
            )
        """))
        connection.execute(text("""
            INSERT INTO dataset_quality_scorecards (id, dataset_id, operation_key, summary)
            VALUES ('scorecard-1', 'dataset-1', 'operation-1', '{}'),
                   ('scorecard-2', 'dataset-1', 'operation-1', '{}')
        """))
        _repair_dataset_quality_scorecard_schema(connection)

    indexes = {index['name'] for index in inspect(legacy_engine).get_indexes('dataset_quality_scorecards')}
    assert 'uq_dataset_quality_operation_key_compat' not in indexes
    assert 'ix_dataset_quality_operation_key_compat' in indexes


def test_database_has_ordered_repair_markers_and_compatible_schema():
    expected = [
        DATASET_QUALITY_SCORECARD_MIGRATION_ID,
        BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID,
        DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID,
        DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID,
    ]
    assert [item.split('_', 2)[1] for item in expected] == ['15', '16', '17', '18']

    inspector = inspect(engine)
    assert 'dataset_versions' in inspector.get_table_names()
    assert 'dataset_quality_scorecards' in inspector.get_table_names()
    assert 'version_signature' in {column['name'] for column in inspector.get_columns('dataset_versions')}
    assert 'completed_at' in {column['name'] for column in inspector.get_columns('dataset_quality_scorecards')}

    with engine.connect() as connection:
        markers = {
            row[0]
            for row in connection.execute(text(
                "SELECT id FROM schema_migrations WHERE id IN (:id15, :id16, :id17, :id18)"
            ), {
                'id15': DATASET_QUALITY_SCORECARD_MIGRATION_ID,
                'id16': BIOMEDICAL_SUBGROUP_ANALYSIS_MIGRATION_ID,
                'id17': DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID,
                'id18': DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID,
            })
        }
    assert markers == set(expected)


def test_apply_migrations_repairs_legacy_database_without_rebuilding_rows(tmp_path, monkeypatch):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-full.sqlite3'}")
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys = OFF"))
        connection.execute(text("DROP TABLE dataset_versions"))
        connection.execute(text("DROP TABLE dataset_quality_scorecards"))
        _legacy_versions_table(connection)
        connection.execute(text("""
            INSERT INTO dataset_versions
                (id, dataset_id, version_number, version_label, content_sha256, schema_fingerprint,
                 target, positive_label, negative_label)
            VALUES
                ('version-1', 'dataset-1', 1, 'v1', 'content-1', 'schema-1',
                 'target', 'positive', 'negative')
        """))
        connection.execute(text("""
            CREATE TABLE dataset_quality_scorecards (
                id VARCHAR(36) PRIMARY KEY,
                dataset_id VARCHAR(36),
                operation_key VARCHAR(128),
                summary JSON
            )
        """))
        connection.execute(text("""
            INSERT INTO dataset_quality_scorecards
                (id, dataset_id, operation_key, summary)
            VALUES
                ('scorecard-1', 'dataset-1', 'operation-1', '{}')
        """))
        connection.execute(text("PRAGMA foreign_keys = ON"))

    monkeypatch.setattr(migrations, "engine", legacy_engine)
    migrations.apply_migrations()
    migrations.apply_migrations()

    inspector = inspect(legacy_engine)
    version_columns = {column['name'] for column in inspector.get_columns('dataset_versions')}
    scorecard_columns = {column['name'] for column in inspector.get_columns('dataset_quality_scorecards')}
    assert 'version_signature' in version_columns
    assert {'schema_version', 'configuration', 'domains', 'provenance', 'completed_at'} <= scorecard_columns
    with legacy_engine.connect() as connection:
        version = connection.execute(text(
            "SELECT version_signature FROM dataset_versions WHERE id = 'version-1'"
        )).scalar_one()
        scorecard = connection.execute(text(
            "SELECT id, operation_key FROM dataset_quality_scorecards WHERE id = 'scorecard-1'"
        )).one()
        markers = {
            row[0]
            for row in connection.execute(text(
                "SELECT id FROM schema_migrations WHERE id IN (:id17, :id18)"
            ), {
                'id17': DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID,
                'id18': DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID,
            })
        }
    assert version == version_signature('content-1', 'schema-1', 'target', 'positive', 'negative')
    assert scorecard == ('scorecard-1', 'operation-1')
    assert markers == {
        DATASET_VERSION_SIGNATURE_REPAIR_MIGRATION_ID,
        DATASET_QUALITY_SCORECARD_REPAIR_MIGRATION_ID,
    }
