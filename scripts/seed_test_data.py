"""Seed test data for local development."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

DATA_DIR = os.environ.get("ONEDRIVE_SYNC_PATH", "./data")


def main():
    # Create test client directory
    client_dir = os.path.join(DATA_DIR, "Contoso")
    os.makedirs(client_dir, exist_ok=True)

    # Sample text document
    with open(os.path.join(client_dir, "project_overview.txt"), "w") as f:
        f.write("""Project Overview: Contoso Digital Transformation

Executive Summary:
Contoso Ltd is undergoing a comprehensive digital transformation initiative
focused on modernizing their legacy ERP systems and migrating to cloud-native
architecture on Microsoft Azure.

Key Stakeholders:
- Sarah Chen, CTO - Executive sponsor
- Marcus Johnson, VP Engineering - Technical lead
- Lisa Park, Director of Operations - Business requirements

Timeline: Q1 2026 - Q4 2026
Budget: $2.5M

Current Pain Points:
1. Legacy on-premise systems with high maintenance costs
2. Data silos across departments
3. Limited real-time analytics capability
4. Manual reporting processes

Strategic Priorities:
1. Cloud migration to Azure
2. Unified data platform
3. Real-time dashboards and reporting
4. API-first architecture
""")

    # Sample meeting notes
    with open(os.path.join(client_dir, "meeting_notes_2026_05.txt"), "w") as f:
        f.write("""Meeting Notes - May 15, 2026
Client: Contoso Ltd
Attendees: Sarah Chen (CTO), Marcus Johnson (VP Eng), Our Team

Discussion:
- Phase 1 migration completed on schedule
- Azure Cosmos DB selected for new customer data store
- Concerns about API gateway performance under load
- Need to finalize container orchestration strategy

Action Items:
1. [Our Team] Prepare performance benchmarks for API gateway - Due: May 22
2. [Marcus] Share current architecture diagrams - Due: May 20
3. [Our Team] Draft proposal for AKS vs Container Apps - Due: May 25
4. [Sarah] Approve Phase 2 budget allocation - Due: May 30

Next Meeting: May 29, 2026
""")

    print(f"Test data created in {client_dir}")
    print("Files:")
    for f in os.listdir(client_dir):
        print(f"  - {f}")


if __name__ == "__main__":
    main()
