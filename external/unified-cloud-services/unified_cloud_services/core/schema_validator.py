"""
Schema Validator

Shared utility for validating BigQuery table schemas and DataFrame schemas before upload.
Provides pre-upload validation to ensure data compatibility.

Usage:
    validator = SchemaValidator()

    # Validate DataFrame before upload
    result = validator.validate_dataframe_schema(df, required_columns=['timestamp', 'instrument_id'])
    if not result.valid:
        raise ValueError(f"Schema validation failed: {result.errors}")

    # Get existing table schema
    schema = await validator.get_table_schema(project_id, dataset, table_name)

    # Check compatibility
    compatible = validator.ensure_schema_compatibility(df, schema)
"""

import logging
from google.cloud import bigquery
import pandas as pd
from google.cloud.exceptions import NotFound

from unified_cloud_services.models.validation import ValidationResult

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates BigQuery table schemas and DataFrame schemas before upload.

    Provides:
    - DataFrame schema validation (required columns, types)
    - BigQuery table schema fetching
    - Schema compatibility checking
    - Schema creation from DataFrame
    """

    def __init__(self, bq_client: bigquery.Client | None = None):
        """
        Initialize schema validator.

        Args:
            bq_client: Optional BigQuery client (creates new one if not provided)
        """
        self.bq_client = bq_client

    def _get_bq_client(self, project_id: str) -> bigquery.Client:
        """Get or create BigQuery client."""
        if self.bq_client:
            return self.bq_client

        from unified_cloud_services.core.cloud_auth_factory import CloudAuthFactory

        return CloudAuthFactory.create_authenticated_bigquery_client(project_id)

    def validate_dataframe_schema(
        self,
        df: pd.DataFrame,
        required_columns: list[str] | None = None,
        optional_columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
    ) -> ValidationResult:
        """
        Validate DataFrame schema before upload.

        Checks:
        - Required columns exist
        - Column types are compatible (if specified)
        - No duplicate columns

        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            optional_columns: List of optional column names (for validation completeness)
            column_types: Dict mapping column names to expected types ('int64', 'float64', 'string', 'timestamp', etc.)

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(
            valid=True,
            validation_type="schema",
            total_records=len(df) if df is not None else 0,
        )

        if df.empty:
            result.valid = False
            result.errors.append("DataFrame is empty")
            return result

        # Check for duplicate columns
        if len(df.columns) != len(set(df.columns)):
            result.valid = False
            result.errors.append("DataFrame has duplicate column names")
            return result

        actual_columns = set(df.columns)

        # Check required columns
        if required_columns:
            missing_columns = set(required_columns) - actual_columns
            if missing_columns:
                result.valid = False
                result.errors.append(f"Missing required columns: {sorted(missing_columns)}")
            else:
                result.stats["required_columns"] = len(required_columns)

        # Check column types (if specified)
        if column_types:
            type_mismatches = []
            for col_name, expected_type in column_types.items():
                if col_name not in df.columns:
                    continue  # Already checked in required_columns

                actual_dtype = str(df[col_name].dtype)

                # Map pandas dtypes to BigQuery types
                type_mapping = {
                    "int64": ["int64", "Int64"],
                    "float64": ["float64", "Float64"],
                    "string": ["object", "string"],
                    "timestamp": ["datetime64[ns]", "datetime64[ns, UTC]"],
                    "bool": ["bool", "boolean"],
                }

                compatible_types = []
                for bq_type, pandas_types in type_mapping.items():
                    if bq_type == expected_type:
                        compatible_types = pandas_types
                        break

                if compatible_types and actual_dtype not in compatible_types:
                    # Check if it's a nullable type (Int64 vs int64)
                    if actual_dtype == "Int64" and expected_type == "int64":
                        continue  # Int64 is compatible with int64
                    if actual_dtype == "Float64" and expected_type == "float64":
                        continue  # Float64 is compatible with float64

                    type_mismatches.append(
                        f"{col_name}: expected {expected_type}, got {actual_dtype}"
                    )

            if type_mismatches:
                result.warnings.append(
                    f"Type mismatches (may still be compatible): {type_mismatches}"
                )

        # Summary
        result.stats["total_columns"] = len(df.columns)
        result.stats["required_columns_checked"] = len(required_columns) if required_columns else 0

        return result

    async def get_table_schema(
        self, project_id: str, dataset: str, table_name: str
    ) -> list[bigquery.SchemaField] | None:
        """
        Get existing table schema from BigQuery.

        Args:
            project_id: GCP project ID
            dataset: BigQuery dataset name
            table_name: Table name

        Returns:
            List of SchemaField objects, or None if table doesn't exist
        """
        try:
            client = self._get_bq_client(project_id)
            table_id = f"{project_id}.{dataset}.{table_name}"

            table = client.get_table(table_id)
            return table.schema

        except NotFound:
            logger.debug(f"Table not found: {table_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return None

    def ensure_schema_compatibility(
        self, df: pd.DataFrame, existing_schema: list[bigquery.SchemaField] | None
    ) -> bool:
        """
        Check if DataFrame schema is compatible with existing BigQuery table schema.

        Args:
            df: DataFrame to check
            existing_schema: Existing table schema (from get_table_schema)

        Returns:
            True if compatible, False otherwise
        """
        if existing_schema is None:
            # No existing schema - always compatible (new table)
            return True

        # Get DataFrame column names
        df_columns = set(df.columns)
        schema_columns = {field.name for field in existing_schema}

        # Check if all required schema columns exist in DataFrame
        required_schema_columns = {
            field.name for field in existing_schema if not field.mode == "NULLABLE"
        }
        missing_required = required_schema_columns - df_columns

        if missing_required:
            logger.warning(f"DataFrame missing required schema columns: {missing_required}")
            return False

        # Check if DataFrame has columns not in schema (may be added)
        extra_columns = df_columns - schema_columns
        if extra_columns:
            logger.info(f"DataFrame has extra columns (will be added to schema): {extra_columns}")

        return True

    def create_schema_from_dataframe(
        self,
        df: pd.DataFrame,
        partition_field: str | None = None,
        clustering_fields: list[str] | None = None,
    ) -> list[bigquery.SchemaField]:
        """
        Create BigQuery schema from DataFrame.

        Args:
            df: DataFrame to create schema from
            partition_field: Optional field for partitioning
            clustering_fields: Optional fields for clustering

        Returns:
            List of SchemaField objects
        """
        schema = []

        # Map pandas dtypes to BigQuery types
        dtype_mapping = {
            "int64": "INTEGER",
            "Int64": "INTEGER",  # Nullable integer
            "float64": "FLOAT",
            "Float64": "FLOAT",  # Nullable float
            "bool": "BOOLEAN",
            "boolean": "BOOLEAN",
            "object": "STRING",
            "string": "STRING",
            "datetime64[ns]": "TIMESTAMP",
            "datetime64[ns, UTC]": "TIMESTAMP",
        }

        for col_name, dtype in df.dtypes.items():
            # Map pandas dtype to BigQuery type
            pandas_dtype = str(dtype)
            bq_type = dtype_mapping.get(pandas_dtype, "STRING")

            # Determine mode (NULLABLE by default, REQUIRED for partition field)
            mode = "REQUIRED" if col_name == partition_field else "NULLABLE"

            # Special handling for timestamp fields
            if "datetime" in pandas_dtype or col_name in [
                "timestamp",
                "timestamp_in",
                "timestamp_out",
                "created_at",
            ]:
                bq_type = "TIMESTAMP"

            schema.append(bigquery.SchemaField(name=col_name, field_type=bq_type, mode=mode))

        return schema

    def schemas_match(
        self, schema1: list[bigquery.SchemaField], schema2: list[bigquery.SchemaField]
    ) -> bool:
        """
        Check if two BigQuery schemas match.

        Args:
            schema1: First schema
            schema2: Second schema

        Returns:
            True if schemas match (same fields, types, modes)
        """
        if len(schema1) != len(schema2):
            return False

        # Create dicts for easier comparison
        schema1_dict = {field.name: (field.field_type, field.mode) for field in schema1}
        schema2_dict = {field.name: (field.field_type, field.mode) for field in schema2}

        # Check all fields match
        for field_name, (field_type, field_mode) in schema1_dict.items():
            if field_name not in schema2_dict:
                return False

            type2, mode2 = schema2_dict[field_name]
            if field_type != type2 or field_mode != mode2:
                return False

        return True

    def validate_bigquery_schema(
        self,
        table_schema: list[bigquery.SchemaField],
        required_fields: list[str] | None = None,
    ) -> ValidationResult:
        """
        Validate BigQuery table schema.

        Args:
            table_schema: BigQuery schema to validate
            required_fields: List of required field names

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(
            valid=True,
            validation_type="bigquery_schema",
            message="BigQuery schema validation",
        )

        if not table_schema:
            result.valid = False
            result.errors.append("Schema is empty")
            return result

        schema_fields = {field.name for field in table_schema}

        # Check required fields
        if required_fields:
            missing_fields = set(required_fields) - schema_fields
            if missing_fields:
                result.valid = False
                result.errors.append(f"Missing required fields: {sorted(missing_fields)}")
            else:
                result.stats["required_fields"] = len(required_fields)

        result.stats["total_fields"] = len(table_schema)

        if result.valid:
            result.message = f"BigQuery schema validation passed: {len(table_schema)} fields"

        return result
