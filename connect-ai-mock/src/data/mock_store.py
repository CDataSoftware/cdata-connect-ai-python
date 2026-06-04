"""
Mock data store for static mode.
Loads and serves mock data from JSON files.
Supports user-based scenarios via username:PAT credentials.
Supports template-based data generation with configurable row counts and pause patterns.
"""
import asyncio
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Tuple

from src.models import ColumnInfo, ResultSet, QueryResult, ErrorDetail

# ---------------------------------------------------------------------------
# Module-level mutable table state for stateful DML support in tests.
# Maps table_key (catalog.schema.table) → list of rows.
# Tables not present fall back to static JSON data.
# DELETE sets the entry to []; INSERT appends to it.
# ---------------------------------------------------------------------------
_mutable_tables: dict[str, list] = {}


class ScenarioConfig:
    """Configuration for a mock scenario."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.description = config.get("description", "")
        self.delay_ms = config.get("delayMs", 0)
        self.error = config.get("error")  # {"code": int, "message": str}
        self.empty_results = config.get("emptyResults", False)
        self.data_dir = config.get("dataDir")  # Custom data subdirectory

        # Template generation settings
        self.row_count = config.get("rowCount")  # Number of rows to generate
        self.pause_after_rows = config.get("pauseAfterRows")  # Pause after N rows

        # Parse pause pattern - supports "20ms", "2s", "1m", or plain numbers (default ms)
        raw_pattern = config.get("pausePattern", [])
        self.pause_pattern_ms = [self._parse_duration(p) for p in raw_pattern]

        # Partial error - if set, rowCount rows are returned then this error is included
        self.partial_error = config.get("partialError")  # {"code": int, "message": str}

        # Truncate response - simulates server crash with incomplete JSON
        self.truncate_after_rows = config.get("truncateAfterRows")  # Cut response after N rows

    @staticmethod
    def _parse_duration(value) -> int:
        """Parse duration string to milliseconds. Supports: '20ms', '2s', '500', 500"""
        if isinstance(value, (int, float)):
            return int(value)  # Assume milliseconds for plain numbers

        if isinstance(value, str):
            value = value.strip().lower()

            # Parse milliseconds: "20ms", "100ms"
            match = re.match(r'^(\d+(?:\.\d+)?)\s*ms$', value)
            if match:
                return int(float(match.group(1)))

            # Parse seconds: "2s", "1.5s"
            match = re.match(r'^(\d+(?:\.\d+)?)\s*s$', value)
            if match:
                return int(float(match.group(1)) * 1000)

            # Parse minutes: "1m", "0.5m"
            match = re.match(r'^(\d+(?:\.\d+)?)\s*m$', value)
            if match:
                return int(float(match.group(1)) * 60 * 1000)

            # Try plain number string
            try:
                return int(float(value))
            except ValueError:
                pass

        return 0  # Default to no delay if unparseable


class MockDataStore:
    """In-memory store for mock data with scenario support."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "static"

        # Scenario configuration
        self.scenarios: dict[str, ScenarioConfig] = {}
        self.credential_map: dict[str, str] = {}  # "user:pat" -> scenario_name

        # Default data (used when no scenario-specific data exists)
        self.catalogs: list[dict] = []
        self.schemas: list[dict] = []
        self.tables: list[dict] = []
        self.columns: list[dict] = []
        self.primary_keys: list[dict] = []
        self.procedures: list[dict] = []
        self.procedure_parameters: list[dict] = []
        self.foreign_keys: list[dict] = []
        self.table_data: dict[str, dict] = {}  # "catalog.schema.table" -> {columns, rows}

        # Scenario-specific data cache
        self.scenario_data: dict[str, dict] = {}  # scenario_name -> {catalogs, tables, etc.}

        self._load_scenarios()
        self._load_data()

    def _load_scenarios(self):
        """Load scenario configuration."""
        scenarios_file = self.data_dir / "scenarios.json"
        if scenarios_file.exists():
            with open(scenarios_file, "r") as f:
                data = json.load(f)

            # Load scenario definitions
            for name, config in data.get("scenarios", {}).items():
                self.scenarios[name] = ScenarioConfig(name, config)

            # Load credential mappings
            self.credential_map = data.get("credentials", {})

            print(f"Loaded {len(self.scenarios)} scenarios")
            print(f"Loaded {len(self.credential_map)} credential mappings")

    def _load_data(self, scenario_data_dir: Path = None):
        """Load all mock data from JSON files."""
        data_dir = scenario_data_dir or self.data_dir

        data = {
            "catalogs": [],
            "schemas": [],
            "tables": [],
            "columns": [],
            "primary_keys": [],
            "procedures": [],
            "procedure_parameters": [],
            "foreign_keys": [],
            "table_data": {}
        }

        # Load each JSON file
        for attr in ["catalogs", "schemas", "tables", "columns",
                     "primary_keys", "procedures", "procedure_parameters", "foreign_keys"]:
            filepath = data_dir / f"{attr}.json"
            if filepath.exists():
                with open(filepath, "r") as f:
                    file_data = json.load(f)
                    data[attr] = file_data.get(attr, file_data) if isinstance(file_data, dict) else file_data

        # Load table data
        tables_subdir = data_dir / "tables"
        if tables_subdir.exists():
            for filepath in tables_subdir.glob("*.json"):
                with open(filepath, "r") as f:
                    table_info = json.load(f)
                    key = f"{table_info.get('catalog', '')}.{table_info.get('schema', '')}.{table_info.get('table', '')}"
                    data["table_data"][key] = table_info

        # If loading default data, set attributes directly
        if scenario_data_dir is None:
            self.catalogs = data["catalogs"]
            self.schemas = data["schemas"]
            self.tables = data["tables"]
            self.columns = data["columns"]
            self.primary_keys = data["primary_keys"]
            self.procedures = data["procedures"]
            self.procedure_parameters = data["procedure_parameters"]
            self.foreign_keys = data["foreign_keys"]
            self.table_data = data["table_data"]

        return data

    def get_scenario(self, credentials: Optional[Tuple[str, str]] = None) -> Optional[ScenarioConfig]:
        """Get scenario config for given credentials."""
        if not credentials:
            return self.scenarios.get("default")

        username, password = credentials
        key = f"{username}:{password}"

        scenario_name = self.credential_map.get(key, "default")
        return self.scenarios.get(scenario_name)

    def get_scenario_data(self, scenario: Optional[ScenarioConfig]) -> dict:
        """Get data for a specific scenario."""
        if not scenario or not scenario.data_dir:
            return {
                "catalogs": self.catalogs,
                "schemas": self.schemas,
                "tables": self.tables,
                "columns": self.columns,
                "primary_keys": self.primary_keys,
                "procedures": self.procedures,
                "procedure_parameters": self.procedure_parameters,
                "foreign_keys": self.foreign_keys,
                "table_data": self.table_data
            }

        # Check cache
        if scenario.name in self.scenario_data:
            return self.scenario_data[scenario.name]

        # Load scenario-specific data
        scenario_dir = self.data_dir / "scenarios" / scenario.data_dir
        if scenario_dir.exists():
            data = self._load_data(scenario_dir)
            self.scenario_data[scenario.name] = data
            return data

        # Fall back to default data
        return self.get_scenario_data(None)

    def _check_scenario_error(self, scenario: Optional[ScenarioConfig]) -> Optional[QueryResult]:
        """Check if scenario should return an error."""
        if scenario and scenario.error:
            return QueryResult(
                results=[],
                error=ErrorDetail(
                    code=scenario.error["code"],
                    message=scenario.error["message"]
                )
            )
        return None

    def _empty_result(self) -> QueryResult:
        """Return an empty result set."""
        return QueryResult(
            results=[ResultSet(schema=[], rows=[], affectedRows=-1)],
            error=None
        )

    # =========================================================================
    # Template Generation Methods
    # =========================================================================

    def _generate_template_value(self, template_str: str, index: int, variables: dict) -> Any:
        """Generate a value from a template string."""
        if not isinstance(template_str, str):
            return template_str

        # {{index}} - row index (1-based)
        if template_str == "{{index}}":
            return index

        # {{random_int:min:max}}
        match = re.match(r'\{\{random_int:(\d+):(\d+)\}\}', template_str)
        if match:
            return random.randint(int(match.group(1)), int(match.group(2)))

        # {{random_float:min:max}}
        match = re.match(r'\{\{random_float:(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)\}\}', template_str)
        if match:
            return round(random.uniform(float(match.group(1)), float(match.group(2))), 2)

        # {{random_bool}}
        if template_str == "{{random_bool}}":
            return random.choice([True, False])

        # {{random_datetime:start:end}}
        match = re.match(r'\{\{random_datetime:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})\}\}', template_str)
        if match:
            start = datetime.strptime(match.group(1), "%Y-%m-%d")
            end = datetime.strptime(match.group(2), "%Y-%m-%d")
            delta = end - start
            random_days = random.randint(0, delta.days)
            random_date = start + timedelta(days=random_days,
                                            hours=random.randint(0, 23),
                                            minutes=random.randint(0, 59),
                                            seconds=random.randint(0, 59))
            return random_date.strftime("%Y-%m-%dT%H:%M:%S")

        # {{uuid}}
        if template_str == "{{uuid}}":
            import uuid
            return str(uuid.uuid4())

        # {{null}} or {{null:probability}}
        if template_str == "{{null}}":
            return None
        match = re.match(r'\{\{null:(\d+(?:\.\d+)?)\}\}', template_str)
        if match:
            if random.random() < float(match.group(1)):
                return None
            return ""  # Will be replaced by other logic if needed

        # Handle variable substitution with {{variable}} and {{index}}
        result = template_str
        result = result.replace("{{index}}", str(index))

        # Handle {{domain}} etc. from variables
        for var_name, var_values in variables.items():
            placeholder = "{{" + var_name + "}}"
            if placeholder in result:
                result = result.replace(placeholder, random.choice(var_values))

        return result

    def _generate_rows_from_template(self, table_info: dict, scenario: ScenarioConfig) -> Tuple[list, float, bool]:
        """
        Generate rows from a template definition.
        Returns (rows, total_pause_time_seconds, should_include_error).
        """
        template = table_info.get("template")
        if not template or not scenario.row_count:
            # No template or row count, return existing rows
            return table_info.get("rows", []), 0, False

        row_template = template.get("row", [])
        variables = template.get("variables", {})
        row_count = scenario.row_count
        pause_after_rows = scenario.pause_after_rows or row_count  # No pause if not set
        pause_pattern = scenario.pause_pattern_ms or []

        # If partialError is set, rowCount rows are returned then error is included
        should_error = scenario.partial_error is not None

        rows = []
        total_pause_ms = 0
        pause_index = 0

        for i in range(1, row_count + 1):
            # Generate row from template
            row = []
            for col_template in row_template:
                value = self._generate_template_value(col_template, i, variables)
                row.append(value)
            rows.append(row)

            # Check if we need to add a pause after this row
            if pause_pattern and pause_after_rows and i % pause_after_rows == 0 and i < row_count:
                pause_ms = pause_pattern[pause_index % len(pause_pattern)]
                total_pause_ms += pause_ms
                pause_index += 1

        return rows, total_pause_ms / 1000.0, should_error  # Return pause in seconds

    def _calculate_template_pause(self, scenario: ScenarioConfig, row_count: int) -> float:
        """Calculate total pause time for template scenario."""
        if not scenario.pause_pattern_ms or not scenario.pause_after_rows:
            return 0

        num_pauses = (row_count - 1) // scenario.pause_after_rows
        if num_pauses <= 0:
            return 0

        total_ms = 0
        for i in range(num_pauses):
            total_ms += scenario.pause_pattern_ms[i % len(scenario.pause_pattern_ms)]

        return total_ms / 1000.0

    # =========================================================================
    # Metadata API Methods
    # =========================================================================

    def get_catalogs(self, workspace: Optional[str] = None,
                    credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get list of catalogs."""
        scenario = self.get_scenario(credentials)

        # Check for error scenario
        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        # Check for empty results scenario
        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="TABLE_CAT", columnLabel="TABLE_CAT", dataType=1,
                      dataTypeName="STRING", ordinal=1)
        ]
        rows = [[c["name"]] for c in data["catalogs"]]

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_schemas(self, catalog_name: Optional[str] = None,
                   schema_name: Optional[str] = None,
                   credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get list of schemas."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="TABLE_SCHEM", columnLabel="TABLE_SCHEM", dataType=1,
                      dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="TABLE_CATALOG", columnLabel="TABLE_CATALOG", dataType=1,
                      dataTypeName="STRING", ordinal=2),
        ]

        rows = []
        for s in data["schemas"]:
            if catalog_name and s.get("catalog") != catalog_name:
                continue
            if schema_name and s.get("name") != schema_name:
                continue
            rows.append([s.get("name"), s.get("catalog")])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_tables(self, catalog_name: Optional[str] = None,
                  schema_name: Optional[str] = None,
                  table_name: Optional[str] = None,
                  table_type: Optional[str] = None,
                  credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get list of tables."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="TABLE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="TABLE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="TABLE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="TABLE_TYPE", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="REMARKS", dataType=1, dataTypeName="STRING", ordinal=5),
        ]

        rows = []
        for t in data["tables"]:
            if catalog_name and t.get("catalog") != catalog_name:
                continue
            if schema_name and t.get("schema") != schema_name:
                continue
            if table_name and t.get("name") != table_name:
                continue
            if table_type and t.get("type") != table_type:
                continue
            rows.append([
                t.get("catalog"),
                t.get("schema"),
                t.get("name"),
                t.get("type", "TABLE"),
                t.get("remarks", "")
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_columns(self, catalog_name: Optional[str] = None,
                   schema_name: Optional[str] = None,
                   table_name: Optional[str] = None,
                   column_name: Optional[str] = None,
                   credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get column metadata."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="TABLE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="TABLE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="TABLE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="COLUMN_NAME", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="DATA_TYPE", dataType=2, dataTypeName="INT", ordinal=5),
            ColumnInfo(columnName="TYPE_NAME", dataType=1, dataTypeName="STRING", ordinal=6),
            ColumnInfo(columnName="COLUMN_SIZE", dataType=2, dataTypeName="INT", ordinal=7),
            ColumnInfo(columnName="NULLABLE", dataType=2, dataTypeName="INT", ordinal=8),
            ColumnInfo(columnName="ORDINAL_POSITION", dataType=2, dataTypeName="INT", ordinal=9),
        ]

        rows = []
        for c in data["columns"]:
            if catalog_name and c.get("catalog") != catalog_name:
                continue
            if schema_name and c.get("schema") != schema_name:
                continue
            if table_name and c.get("table") != table_name:
                continue
            if column_name and c.get("name") != column_name:
                continue
            rows.append([
                c.get("catalog"),
                c.get("schema"),
                c.get("table"),
                c.get("name"),
                c.get("dataType", 1),
                c.get("typeName", "STRING"),
                c.get("size", 255),
                1 if c.get("nullable", True) else 0,
                c.get("ordinal", 1)
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_primary_keys(self, catalog_name: Optional[str] = None,
                        schema_name: Optional[str] = None,
                        table_name: Optional[str] = None,
                        credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get primary key information."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="TABLE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="TABLE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="TABLE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="COLUMN_NAME", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="KEY_SEQ", dataType=2, dataTypeName="INT", ordinal=5),
            ColumnInfo(columnName="PK_NAME", dataType=1, dataTypeName="STRING", ordinal=6),
        ]

        rows = []
        for pk in data["primary_keys"]:
            if catalog_name and pk.get("catalog") != catalog_name:
                continue
            if schema_name and pk.get("schema") != schema_name:
                continue
            if table_name and pk.get("table") != table_name:
                continue
            rows.append([
                pk.get("catalog"),
                pk.get("schema"),
                pk.get("table"),
                pk.get("column"),
                pk.get("keySeq", 1),
                pk.get("pkName", "")
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_procedures(self, catalog_name: Optional[str] = None,
                      schema_name: Optional[str] = None,
                      procedure_name: Optional[str] = None,
                      credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get stored procedures."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="PROCEDURE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="PROCEDURE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="PROCEDURE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="REMARKS", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="PROCEDURE_TYPE", dataType=2, dataTypeName="INT", ordinal=5),
        ]

        rows = []
        for p in data["procedures"]:
            if catalog_name and p.get("catalog") != catalog_name:
                continue
            if schema_name and p.get("schema") != schema_name:
                continue
            if procedure_name and p.get("name") != procedure_name:
                continue
            rows.append([
                p.get("catalog"),
                p.get("schema"),
                p.get("name"),
                p.get("remarks", ""),
                p.get("type", 2)
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_procedure_parameters(self, catalog_name: Optional[str] = None,
                                schema_name: Optional[str] = None,
                                procedure_name: Optional[str] = None,
                                param_name: Optional[str] = None,
                                credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get procedure parameters."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="PROCEDURE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="PROCEDURE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="PROCEDURE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="COLUMN_NAME", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="COLUMN_TYPE", dataType=2, dataTypeName="INT", ordinal=5),
            ColumnInfo(columnName="DATA_TYPE", dataType=2, dataTypeName="INT", ordinal=6),
            ColumnInfo(columnName="TYPE_NAME", dataType=1, dataTypeName="STRING", ordinal=7),
        ]

        rows = []
        for pp in data["procedure_parameters"]:
            if catalog_name and pp.get("catalog") != catalog_name:
                continue
            if schema_name and pp.get("schema") != schema_name:
                continue
            if procedure_name and pp.get("procedure") != procedure_name:
                continue
            if param_name and pp.get("name") != param_name:
                continue
            rows.append([
                pp.get("catalog"),
                pp.get("schema"),
                pp.get("procedure"),
                pp.get("name"),
                pp.get("columnType", 1),
                pp.get("dataType", 1),
                pp.get("typeName", "STRING")
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    def get_exported_keys(self, catalog_name: Optional[str] = None,
                         schema_name: Optional[str] = None,
                         table_name: Optional[str] = None,
                         credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get exported (foreign) keys where table is parent."""
        return self._get_foreign_keys(catalog_name, schema_name, table_name, is_exported=True, credentials=credentials)

    def get_imported_keys(self, catalog_name: Optional[str] = None,
                         schema_name: Optional[str] = None,
                         table_name: Optional[str] = None,
                         credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get imported keys where table is child."""
        return self._get_foreign_keys(catalog_name, schema_name, table_name, is_exported=False, credentials=credentials)

    def _get_foreign_keys(self, catalog_name: Optional[str],
                         schema_name: Optional[str],
                         table_name: Optional[str],
                         is_exported: bool,
                         credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Get foreign key relationships."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        schema = [
            ColumnInfo(columnName="PKTABLE_CAT", dataType=1, dataTypeName="STRING", ordinal=1),
            ColumnInfo(columnName="PKTABLE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=2),
            ColumnInfo(columnName="PKTABLE_NAME", dataType=1, dataTypeName="STRING", ordinal=3),
            ColumnInfo(columnName="PKCOLUMN_NAME", dataType=1, dataTypeName="STRING", ordinal=4),
            ColumnInfo(columnName="FKTABLE_CAT", dataType=1, dataTypeName="STRING", ordinal=5),
            ColumnInfo(columnName="FKTABLE_SCHEM", dataType=1, dataTypeName="STRING", ordinal=6),
            ColumnInfo(columnName="FKTABLE_NAME", dataType=1, dataTypeName="STRING", ordinal=7),
            ColumnInfo(columnName="FKCOLUMN_NAME", dataType=1, dataTypeName="STRING", ordinal=8),
            ColumnInfo(columnName="KEY_SEQ", dataType=2, dataTypeName="INT", ordinal=9),
            ColumnInfo(columnName="FK_NAME", dataType=1, dataTypeName="STRING", ordinal=10),
            ColumnInfo(columnName="PK_NAME", dataType=1, dataTypeName="STRING", ordinal=11),
        ]

        rows = []
        for fk in data["foreign_keys"]:
            # For exported keys, filter by PK table; for imported, filter by FK table
            if is_exported:
                match_catalog = fk.get("pkCatalog")
                match_schema = fk.get("pkSchema")
                match_table = fk.get("pkTable")
            else:
                match_catalog = fk.get("fkCatalog")
                match_schema = fk.get("fkSchema")
                match_table = fk.get("fkTable")

            if catalog_name and match_catalog != catalog_name:
                continue
            if schema_name and match_schema != schema_name:
                continue
            if table_name and match_table != table_name:
                continue

            rows.append([
                fk.get("pkCatalog"),
                fk.get("pkSchema"),
                fk.get("pkTable"),
                fk.get("pkColumn"),
                fk.get("fkCatalog"),
                fk.get("fkSchema"),
                fk.get("fkTable"),
                fk.get("fkColumn"),
                fk.get("keySeq", 1),
                fk.get("fkName", ""),
                fk.get("pkName", "")
            ])

        return QueryResult(
            results=[ResultSet(schema=schema, rows=rows, affectedRows=-1)],
            error=None
        )

    # =========================================================================
    # SQL API Methods
    # =========================================================================

    @staticmethod
    def _substitute_parameters(query: str, parameters: Optional[dict]) -> str:
        """Replace @param placeholders with literal values from parameters dict."""
        if not parameters:
            return query
        for key, param in parameters.items():
            if isinstance(param, dict):
                value = param.get("value")
            elif hasattr(param, "value"):
                value = param.value
            else:
                value = param
            if value is None:
                literal = "NULL"
            elif isinstance(value, str):
                literal = f"'{value}'"
            else:
                literal = str(value)
            query = query.replace(key, literal)
        return query

    def execute_query(self, query: str, default_catalog: Optional[str] = None,
                     default_schema: Optional[str] = None,
                     schema_only: bool = False,
                     parameters: Optional[dict] = None,
                     credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Execute a SQL query and return mock results."""
        query = self._substitute_parameters(query, parameters)
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        # Non-SELECT statements (DELETE, INSERT, UPDATE, CREATE, DROP, etc.)
        # have no result set.  For DELETE and INSERT we also mutate the
        # in-memory table state so that a subsequent SELECT sees the change.
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
            table_key = self._extract_table_from_dml(query, default_catalog, default_schema)
            if table_key:
                if query_upper.startswith("DELETE"):
                    _mutable_tables[table_key] = []
                elif query_upper.startswith("INSERT"):
                    value = self._parse_insert_value(query)
                    if table_key not in _mutable_tables:
                        _mutable_tables[table_key] = []
                    _mutable_tables[table_key].append([value])
            return QueryResult(
                results=[ResultSet(schema=[], rows=[], affectedRows=0)],
                error=None,
            )

        if scenario and scenario.empty_results:
            return self._empty_result()

        data = self.get_scenario_data(scenario)

        # Simple query parsing to extract table name
        table_key = self._extract_table_from_query(query, default_catalog, default_schema)

        if table_key and table_key in data["table_data"]:
            table_info = data["table_data"][table_key]
            columns = table_info.get("columns", [])

            # Check if this is a template-based table with row generation
            partial_error = None
            if not schema_only and table_info.get("template") and scenario and scenario.row_count:
                rows, pause_seconds, should_error = self._generate_rows_from_template(table_info, scenario)
                # Apply the calculated pause (simulates streaming delay)
                if pause_seconds > 0:
                    time.sleep(pause_seconds)
                # Check if we should include a partial error
                if should_error and scenario.partial_error:
                    partial_error = ErrorDetail(
                        code=scenario.partial_error["code"],
                        message=scenario.partial_error["message"]
                    )
            else:
                if schema_only:
                    rows = []
                elif table_key in _mutable_tables:
                    rows = _mutable_tables[table_key]
                else:
                    rows = table_info.get("rows", [])

            result_schema = [
                ColumnInfo(
                    catalogName=table_info.get("catalog", ""),
                    schemaName=table_info.get("schema", ""),
                    tableName=table_info.get("table", ""),
                    columnName=c.get("name", ""),
                    columnLabel=c.get("label", c.get("name", "")),
                    dataType=c.get("dataType", 1),
                    dataTypeName=c.get("dataTypeName", "STRING"),
                    length=c.get("length", 255),
                    nullable=c.get("nullable", True),
                    ordinal=i + 1
                )
                for i, c in enumerate(columns)
            ]

            return QueryResult(
                results=[ResultSet(schema=result_schema, rows=rows, affectedRows=-1)],
                error=partial_error
            )

        # Return empty result if no matching table found
        return QueryResult(
            results=[ResultSet(schema=[], rows=[], affectedRows=-1)],
            error=None
        )

    def execute_batch(self, query: str, parameters: Optional[list] = None,
                     default_catalog: Optional[str] = None,
                     default_schema: Optional[str] = None,
                     credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Execute a batch operation (INSERT/UPDATE/DELETE)."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        if scenario and scenario.empty_results:
            return QueryResult(
                results=[ResultSet(schema=[], rows=[], affectedRows=0)],
                error=None
            )

        # For parameterized batch INSERTs, update the in-memory table state
        # so a subsequent SELECT reflects the inserted rows.
        if query.strip().upper().startswith("INSERT") and parameters:
            table_key = self._extract_table_from_dml(query, default_catalog, default_schema)
            if table_key:
                if table_key not in _mutable_tables:
                    _mutable_tables[table_key] = []
                for param_set in parameters:
                    value = self._resolve_batch_insert_value(query, param_set)
                    _mutable_tables[table_key].append([value])

        affected = len(parameters) if parameters else 1
        return QueryResult(
            results=[ResultSet(schema=[], rows=[], affectedRows=affected)],
            error=None
        )

    def execute_procedure(self, procedure: str, parameters: Optional[dict] = None,
                         default_catalog: Optional[str] = None,
                         default_schema: Optional[str] = None,
                         credentials: Optional[Tuple[str, str]] = None) -> QueryResult:
        """Execute a stored procedure, looking up a static result file by name."""
        scenario = self.get_scenario(credentials)

        error_result = self._check_scenario_error(scenario)
        if error_result:
            return error_result

        # Strip brackets/quotes and split into catalog.schema.procedure parts
        clean_proc = re.sub(r'[\[\]`"]', '', procedure)
        parts = clean_proc.split('.')
        proc_name = parts[-1] if parts else clean_proc
        catalog = parts[0] if len(parts) >= 3 else (default_catalog or "")
        schema = parts[1] if len(parts) >= 3 else (default_schema or "")

        # Look for a procedure result file: procedure_results/{catalog}.{schema}.{proc}.json
        proc_key = f"{catalog}.{schema}.{proc_name}"
        proc_file = self.data_dir / "procedure_results" / f"{proc_key}.json"

        if proc_file.exists():
            with open(proc_file, "r") as f:
                proc_info = json.load(f)

            columns = proc_info.get("columns", [])
            rows = proc_info.get("rows", [])

            result_schema = [
                ColumnInfo(
                    catalogName=proc_info.get("catalog", catalog),
                    schemaName=proc_info.get("schema", schema),
                    tableName=proc_info.get("procedure", proc_name),
                    columnName=c.get("name", ""),
                    columnLabel=c.get("label", c.get("name", "")),
                    dataType=c.get("dataType", 1),
                    dataTypeName=c.get("dataTypeName", "VARCHAR"),
                    length=c.get("length", 255),
                    nullable=c.get("nullable", True),
                    ordinal=i + 1,
                )
                for i, c in enumerate(columns)
            ]

            return QueryResult(
                results=[ResultSet(schema=result_schema, rows=rows, affectedRows=-1)],
                error=None,
            )

        # Default: empty success result (procedure not found in static files)
        return QueryResult(
            results=[ResultSet(schema=[], rows=[], affectedRows=-1)],
            error=None,
        )

    def _extract_table_from_dml(self, query: str, default_catalog: Optional[str],
                                default_schema: Optional[str]) -> Optional[str]:
        """Extract table key from INSERT INTO or DELETE FROM statements."""
        match = re.search(r'\b(?:FROM|INTO)\s+([^\s,;()]+)', query, re.IGNORECASE)
        if not match:
            return None
        table_ref = re.sub(r'[\[\]`"]', '', match.group(1))
        parts = table_ref.split('.')
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 2:
            # Two-part name is schema.table, not catalog.table
            catalog = default_catalog or ""
            return f"{catalog}.{parts[0]}.{parts[1]}"
        elif len(parts) == 1:
            catalog = default_catalog or ""
            schema = default_schema or ""
            return f"{catalog}.{schema}.{parts[0]}"
        return None

    def _parse_insert_value(self, query: str) -> Any:
        """Parse the single-column literal VALUES clause of an INSERT statement."""
        match = re.search(r'\bVALUES\s*\(\s*(.*?)\s*\)', query, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        raw = match.group(1).strip()
        if raw.upper() == 'NULL':
            return None
        if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
            return raw[1:-1]
        return raw  # Unquoted value (e.g. from pyformat % substitution)

    def _resolve_batch_insert_value(self, query: str, param_set: dict) -> Any:
        """Resolve the INSERT value from a parameterized batch parameter set."""
        match = re.search(r'\bVALUES\s*\(\s*(.*?)\s*\)', query, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        raw = match.group(1).strip()
        if raw.startswith("@") and raw in param_set:
            param_info = param_set[raw]
            if isinstance(param_info, dict):
                return param_info.get("value")
        return self._parse_insert_value(query)

    def _extract_table_from_query(self, query: str, default_catalog: Optional[str],
                                  default_schema: Optional[str]) -> Optional[str]:
        """Extract table reference from SQL query."""
        import re

        # Simple regex to find FROM clause
        match = re.search(r'\bFROM\s+([^\s,;()]+)', query, re.IGNORECASE)
        if not match:
            return None

        table_ref = re.sub(r'[\[\]`"]', '', match.group(1))
        parts = table_ref.split('.')

        if len(parts) == 3:
            # catalog.schema.table
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 2:
            # Two-part name is schema.table
            catalog = default_catalog or ""
            return f"{catalog}.{parts[0]}.{parts[1]}"
        elif len(parts) == 1:
            # just table
            catalog = default_catalog or ""
            schema = default_schema or ""
            return f"{catalog}.{schema}.{parts[0]}"

        return None


# Global instance
_store: Optional[MockDataStore] = None


def get_store() -> MockDataStore:
    """Get the global mock data store instance."""
    global _store
    if _store is None:
        _store = MockDataStore()
    return _store


def init_store(data_dir: str = None):
    """Initialize the mock data store with a custom data directory."""
    global _store
    _store = MockDataStore(data_dir)
    return _store
