# Current Fixture Data Dictionary

## Status

The only database schema in the repository is a small synthetic connectivity
fixture. It is not a complete i2b2 schema, an AKTIN concept hierarchy, or the
planned synthetic AKTIN/i2b2 evaluation dataset. The source explicitly says it
must be replaced before evaluation.

## Relation

| Schema | Table | Column | Type | Constraint | Meaning in fixture |
|---|---|---|---|---|---|
| `public` | `patient_dimension` | `patient_num` | `BIGINT` | Primary key | Synthetic row identifier |

The initialization SQL inserts values generated from 1 through 20, one row
per synthetic fixture patient. The gateway never projects this identifier; it
currently supports only a row count. No clinical variables, concept mappings,
relationships, or event tables are defined here.

The schema MCP context describes the same table and identifies the dataset as
`synthetic-connectivity-fixture`. The database initialization only runs when a
new PostgreSQL data volume is initialized. The bundled role/database setup has
inconsistent names; consult [Operations](operations.md#compose-database-initialization)
before treating the local database as initialized.

## Evaluation data

No evaluation dataset, data-generation script, or evaluation script is present
in the tracked repository. The source and generation method for the future
synthetic AKTIN/i2b2 dataset and concept hierarchy remain open in Decision
D-014.
