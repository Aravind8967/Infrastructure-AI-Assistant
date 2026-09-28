import json, os
import psycopg2
from psycopg2.extras import execute_batch


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "incident_db",
    "user": "incident_ingest",
    "password": "ingest_password",
}

JSON_FILE = "incident_management_500.json"


def build_document_text(incident):
    """
    Convert structured incident information into a text document
    that we will later send to the embedding model.
    """

    return f"""
Incident ID: {incident["incident_id"]}

Problem:
{incident["short_description"]}

Description:
{incident["description"]}

Category:
{incident["category"]}

Subcategory:
{incident["subcategory"]}

Assignment Group:
{incident["assignment_group"]}

Service:
{incident["service"]}

Criticality:
{incident["criticality_description"]}

State:
{incident["state"]}

Root Cause:
{incident["root_cause_analysis"] or "Not available"}

Resolution:
{incident["resolution"] or "Not available"}
""".strip()


def load_json():
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "incidents" not in data:
        raise ValueError("JSON does not contain an 'incidents' field")

    incidents = data["incidents"]

    if not isinstance(incidents, list):
        raise ValueError("'incidents' must be a list")

    return data, incidents


def validate_incident(incident):
    required_fields = [
        "incident_id",
        "short_description",
        "description",
        "category",
        "subcategory",
        "assignment_group",
        "assigned_to",
        "criticality",
        "criticality_description",
        "state",
        "opened_at",
        "closed_at",
        "opened_by",
        "closed_by",
        "resolution",
        "root_cause_analysis",
        "service",
    ]

    for field in required_fields:
        if field not in incident:
            raise ValueError(
                f"Incident {incident.get('incident_id')} "
                f"is missing field: {field}"
            )


def prepare_incident(incident):
    validate_incident(incident)

    document_text = build_document_text(incident)

    return (
        incident["incident_id"],
        incident["short_description"],
        incident["description"],
        incident["category"],
        incident["subcategory"],
        incident["assignment_group"],
        incident["assigned_to"],
        incident["criticality"],
        incident["criticality_description"],
        incident["state"],
        incident["opened_at"],
        incident["closed_at"],
        incident["opened_by"],
        incident["closed_by"],
        incident["resolution"],
        incident["root_cause_analysis"],
        incident["service"],
        document_text,
    )


def insert_incidents(incidents):
    connection = psycopg2.connect(**DB_CONFIG)

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO incident.incidents (
                incident_id,
                short_description,
                description,
                category,
                subcategory,
                assignment_group,
                assigned_to,
                criticality,
                criticality_description,
                state,
                opened_at,
                closed_at,
                opened_by,
                closed_by,
                resolution,
                root_cause_analysis,
                service,
                document_text
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        rows = [
            prepare_incident(incident)
            for incident in incidents
        ]

        execute_batch(
            cursor,
            query,
            rows,
            page_size=100
        )

        connection.commit()

        print(f"Successfully inserted {len(rows)} incidents.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def main():
    dataset, incidents = load_json()

    print(f"Dataset: {dataset['dataset_name']}")
    print(f"Expected records: {dataset['record_count']}")
    print(f"Records found: {len(incidents)}")

    if len(incidents) != dataset["record_count"]:
        raise ValueError(
            "Dataset record count does not match "
            "the number of incidents."
        )

    insert_incidents(incidents)




if __name__ == "__main__":
    main()

    # with open(JSON_FILE, 'r', encoding="utf-8") as f:
    #     data = json.load(f)

    # print(data)
