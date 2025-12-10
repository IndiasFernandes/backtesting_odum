"""
Table Manager

Centralized BigQuery table creation and management with partitioning and clustering.
Eliminates duplication across services for table setup patterns.

Usage:
    manager = TableManager(cloud_service)
    await manager.ensure_table(
        target=cloud_target,
        table_name='features_5m',
        schema=schema_fields,
        partition_field='timestamp',
        clustering_fields=['instrument_id']
    )
"""

import logging
from typing import Any
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from unified_cloud_services.core.cloud_config import CloudTarget
from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.schema_validator import SchemaValidator
from unified_cloud_services.core.cloud_auth_factory import CloudAuthFactory

logger = logging.getLogger(__name__)


class TableManager:
    """
    Centralized BigQuery table management with partitioning and clustering.

    Handles:
    - Table creation with proper partitioning (DAY by default)
    - Clustering configuration
    - Schema validation and updates
    - Table existence checking
    """

    def __init__(
        self,
        cloud_service: UnifiedCloudService,
        schema_validator: SchemaValidator | None = None,
    ):
        """
        Initialize table manager.

        Args:
            cloud_service: UnifiedCloudService instance
            schema_validator: Optional SchemaValidator (creates new one if not provided)
        """
        self.cloud_service = cloud_service
        self.schema_validator = schema_validator or SchemaValidator()

    async def ensure_table(
        self,
        target: CloudTarget,
        table_name: str,
        schema: list[bigquery.SchemaField] | None = None,
        partition_field: str | None = "timestamp",
        partition_type: bigquery.TimePartitioningType = bigquery.TimePartitioningType.DAY,
        clustering_fields: list[str] | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> bool:
        """
        Ensure table exists with correct schema, partitioning, and clustering.

        Creates table if it doesn't exist, or validates schema if it does.

        Args:
            target: CloudTarget configuration
            table_name: Table name (without project.dataset prefix)
            schema: Optional schema fields (auto-detected if not provided)
            partition_field: Field for partitioning (default: 'timestamp')
            partition_type: Partitioning type (default: DAY)
            clustering_fields: Fields for clustering (e.g., ['instrument_id', 'venue'])
            description: Optional table description
            labels: Optional table labels

        Returns:
            True if table is ready, False otherwise
        """
        try:

            bq_client = CloudAuthFactory.create_authenticated_bigquery_client(target.project_id)
            full_table_id = f"{target.project_id}.{target.bigquery_dataset}.{table_name}"

            # Check if table exists
            try:
                existing_table = bq_client.get_table(full_table_id)

                # Validate schema if provided
                if schema:
                    existing_schema = existing_table.schema
                    if not self.schema_validator.schemas_match(existing_schema, schema):
                        logger.warning(
                            f"⚠️ Schema mismatch for {table_name}, but table exists. Consider recreating."
                        )

                # Check partitioning
                if partition_field and existing_table.time_partitioning:
                    if existing_table.time_partitioning.field != partition_field:
                        logger.warning(
                            f"⚠️ Partition field mismatch: existing={existing_table.time_partitioning.field}, "
                            f"expected={partition_field}"
                        )

                # Check clustering
                if clustering_fields and existing_table.clustering_fields:
                    if set(existing_table.clustering_fields) != set(clustering_fields):
                        logger.warning(
                            f"⚠️ Clustering mismatch: existing={existing_table.clustering_fields}, "
                            f"expected={clustering_fields}"
                        )

                logger.debug(f"✅ Table exists: {table_name}")
                return True

            except NotFound:
                # Table doesn't exist, create it
                logger.info(f"📊 Creating table: {table_name}")

                # Ensure dataset exists
                dataset_ref = bigquery.DatasetReference(target.project_id, target.bigquery_dataset)
                try:
                    bq_client.get_dataset(dataset_ref)
                except NotFound:
                    dataset = bigquery.Dataset(dataset_ref)
                    dataset.location = target.bigquery_location or "asia-northeast1"
                    bq_client.create_dataset(dataset, exists_ok=False)
                    logger.info(f"✅ Created dataset: {target.bigquery_dataset}")

                # Create table
                table_ref = bigquery.TableReference(dataset_ref, table_name)
                table = bigquery.Table(table_ref, schema=schema)

                # Set partitioning
                if partition_field:
                    table.time_partitioning = bigquery.TimePartitioning(
                        type_=partition_type, field=partition_field
                    )
                    logger.debug(
                        f"✅ Configured partitioning: {partition_field} ({partition_type})"
                    )

                # Set clustering
                if clustering_fields:
                    table.clustering_fields = clustering_fields
                    logger.debug(f"✅ Configured clustering: {clustering_fields}")

                # Set description
                if description:
                    table.description = description

                # Set labels
                if labels:
                    table.labels = labels

                # Create table
                created_table = bq_client.create_table(table)
                logger.info(
                    f"✅ Created table: {table_name} with {len(created_table.schema)} fields"
                )

                return True

        except Exception as e:
            logger.error(f"❌ Failed to ensure table {table_name}: {e}")
            return False

    async def get_table_info(self, target: CloudTarget, table_name: str) -> dict[str, Any] | None:
        """
        Get table information including schema, partitioning, and clustering.

        Args:
            target: CloudTarget configuration
            table_name: Table name (without project.dataset prefix)

        Returns:
            Dict with table info or None if table doesn't exist
        """
        try:
            bq_client = CloudAuthFactory.create_authenticated_bigquery_client(target.project_id)
            full_table_id = f"{target.project_id}.{target.bigquery_dataset}.{table_name}"

            table = bq_client.get_table(full_table_id)

            return {
                "table_id": full_table_id,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created,
                "modified": table.modified,
                "schema": table.schema,
                "time_partitioning": (
                    {
                        "field": (
                            table.time_partitioning.field if table.time_partitioning else None
                        ),
                        "type": (
                            str(table.time_partitioning.type_) if table.time_partitioning else None
                        ),
                    }
                    if table.time_partitioning
                    else None
                ),
                "clustering_fields": table.clustering_fields,
                "description": table.description,
                "labels": table.labels,
            }

        except NotFound:
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get table info for {table_name}: {e}")
            return None

    def create_table_config(
        self,
        partition_field: str | None = "timestamp",
        partition_type: bigquery.TimePartitioningType = bigquery.TimePartitioningType.DAY,
        clustering_fields: list[str] | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create table configuration dict for use with upload methods.

        Helper method to create consistent table configs across services.

        Args:
            partition_field: Field for partitioning
            partition_type: Partitioning type
            clustering_fields: Fields for clustering
            description: Table description
            labels: Table labels

        Returns:
            Dict with table configuration
        """
        config = {}

        if partition_field:
            config["partition_field"] = partition_field
            config["partition_type"] = partition_type

        if clustering_fields:
            config["clustering_fields"] = clustering_fields

        if description:
            config["description"] = description

        if labels:
            config["labels"] = labels

        return config
