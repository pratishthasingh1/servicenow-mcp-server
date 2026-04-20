"""ServiceNow MCP Server — change request management via the Model Context Protocol."""

from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from models import (
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ChangeState,
    ChangeType,
    Impact,
    Priority,
    Risk,
)
from servicenow_client import ServiceNowAPIError, ServiceNowClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("servicenow-mcp")

mcp = FastMCP(
    "servicenow",
    instructions="Manage ServiceNow change requests — create, read, update, list, search, add work notes, and check approval status.",
)

_client: Optional[ServiceNowClient] = None


def _get_client() -> ServiceNowClient:
    global _client
    if _client is None:
        _client = ServiceNowClient()
    return _client


def _pretty(data: dict | list) -> str:
    return json.dumps(data, indent=2, default=str)


# ── Tool: Create Change Request ────────────────────────────────────────

@mcp.tool()
async def create_change_request(
    short_description: str,
    description: str | None = None,
    type: str = "standard",
    category: str | None = None,
    risk: str = "3",
    impact: str = "3",
    priority: str = "3",
    assignment_group: str | None = None,
    assigned_to: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    implementation_plan: str | None = None,
    backout_plan: str | None = None,
    test_plan: str | None = None,
    justification: str | None = None,
    std_change_producer_version: str | None = None,
) -> str:
    """Create a new ServiceNow change request.

    Args:
        short_description: Brief summary of the change (required).
        description: Detailed description of the change.
        type: Change type — "standard", "normal", or "emergency". Defaults to "standard".
        category: Category (e.g. "Software", "Hardware", "Network").
        risk: Risk level — "1" (High), "2" (Moderate), "3" (Low), "4" (None). Defaults to "3".
        impact: Impact level — "1" (High), "2" (Medium), "3" (Low). Defaults to "3".
        priority: Priority — "1" (Critical) through "5" (Planning). Defaults to "3".
        assignment_group: Name or sys_id of the assignment group.
        assigned_to: Username or sys_id of the assignee.
        start_date: Planned start date in "YYYY-MM-DD HH:MM:SS" format.
        end_date: Planned end date in "YYYY-MM-DD HH:MM:SS" format.
        implementation_plan: Steps to implement the change.
        backout_plan: Steps to revert if the change fails.
        test_plan: Steps to verify the change.
        justification: Business justification for the change.
        std_change_producer_version: Sys_id of a standard change template.
    """
    try:
        cr = ChangeRequestCreate(
            short_description=short_description,
            description=description,
            type=ChangeType(type),
            category=category,
            risk=Risk(risk),
            impact=Impact(impact),
            priority=Priority(priority),
            assignment_group=assignment_group,
            assigned_to=assigned_to,
            start_date=start_date,
            end_date=end_date,
            implementation_plan=implementation_plan,
            backout_plan=backout_plan,
            test_plan=test_plan,
            justification=justification,
            std_change_producer_version=std_change_producer_version,
        )
        result = await _get_client().create_change_request(cr.to_snow_payload())
        return f"Change request created successfully:\n{_pretty(result)}"
    except ServiceNowAPIError as e:
        return f"Error creating change request: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: Get Change Request ───────────────────────────────────────────

@mcp.tool()
async def get_change_request(identifier: str) -> str:
    """Retrieve a ServiceNow change request by its CHG number or sys_id.

    Args:
        identifier: The change request number (e.g. "CHG0012345") or sys_id.
    """
    try:
        result = await _get_client().get_change_request(identifier)
        return _pretty(result)
    except ServiceNowAPIError as e:
        return f"Error: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: Update Change Request ────────────────────────────────────────

@mcp.tool()
async def update_change_request(
    identifier: str,
    short_description: str | None = None,
    description: str | None = None,
    state: str | None = None,
    category: str | None = None,
    risk: str | None = None,
    impact: str | None = None,
    priority: str | None = None,
    assignment_group: str | None = None,
    assigned_to: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    implementation_plan: str | None = None,
    backout_plan: str | None = None,
    test_plan: str | None = None,
    close_code: str | None = None,
    close_notes: str | None = None,
) -> str:
    """Update fields on an existing ServiceNow change request.

    Args:
        identifier: The change request number (e.g. "CHG0012345") or sys_id.
        short_description: Updated summary.
        description: Updated description.
        state: New state — "-5" (New), "-4" (Assess), "-3" (Authorize), "-2" (Scheduled), "-1" (Implement), "0" (Review), "3" (Closed), "4" (Canceled).
        category: Updated category.
        risk: Updated risk level — "1" (High), "2" (Moderate), "3" (Low), "4" (None).
        impact: Updated impact — "1" (High), "2" (Medium), "3" (Low).
        priority: Updated priority — "1" (Critical) through "5" (Planning).
        assignment_group: Updated assignment group.
        assigned_to: Updated assignee.
        start_date: Updated planned start date.
        end_date: Updated planned end date.
        implementation_plan: Updated implementation steps.
        backout_plan: Updated backout steps.
        test_plan: Updated test steps.
        close_code: Close code (e.g. "successful").
        close_notes: Close notes.
    """
    try:
        update = ChangeRequestUpdate(
            short_description=short_description,
            description=description,
            state=ChangeState(state) if state else None,
            category=category,
            risk=Risk(risk) if risk else None,
            impact=Impact(impact) if impact else None,
            priority=Priority(priority) if priority else None,
            assignment_group=assignment_group,
            assigned_to=assigned_to,
            start_date=start_date,
            end_date=end_date,
            implementation_plan=implementation_plan,
            backout_plan=backout_plan,
            test_plan=test_plan,
            close_code=close_code,
            close_notes=close_notes,
        )
        payload = update.to_snow_payload()
        if not payload:
            return "No fields provided to update."
        result = await _get_client().update_change_request(identifier, payload)
        return f"Change request updated successfully:\n{_pretty(result)}"
    except ServiceNowAPIError as e:
        return f"Error updating change request: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: List Change Requests ─────────────────────────────────────────

@mcp.tool()
async def list_change_requests(
    state: str | None = None,
    assignment_group: str | None = None,
    assigned_to: str | None = None,
    type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List ServiceNow change requests with optional filters.

    Args:
        state: Filter by state — e.g. "-5" (New), "-2" (Scheduled), "3" (Closed).
        assignment_group: Filter by assignment group name.
        assigned_to: Filter by assignee username.
        type: Filter by change type — "standard", "normal", or "emergency".
        limit: Max number of results (default 20, max 100).
        offset: Pagination offset (default 0).
    """
    try:
        query_parts: list[str] = []
        if state:
            query_parts.append(f"state={state}")
        if assignment_group:
            query_parts.append(f"assignment_group.name={assignment_group}")
        if assigned_to:
            query_parts.append(f"assigned_to.user_name={assigned_to}")
        if type:
            query_parts.append(f"type={type}")
        query = "^".join(query_parts)

        results = await _get_client().list_change_requests(
            query=query,
            limit=min(limit, 100),
            offset=offset,
        )
        if not results:
            return "No change requests found matching the criteria."
        return f"Found {len(results)} change request(s):\n{_pretty(results)}"
    except ServiceNowAPIError as e:
        return f"Error listing change requests: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: Search Change Requests ───────────────────────────────────────

@mcp.tool()
async def search_change_requests(
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Search ServiceNow change requests using a text query or encoded query string.

    Supports both free-text search (searched in short_description and description)
    and ServiceNow encoded queries (e.g. "priority=1^state=-2").

    Args:
        query: Search text or ServiceNow encoded query string.
        limit: Max number of results (default 20, max 100).
        offset: Pagination offset (default 0).
    """
    try:
        if "=" in query or "^" in query:
            encoded_query = query
        else:
            encoded_query = f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}"

        results = await _get_client().list_change_requests(
            query=encoded_query,
            limit=min(limit, 100),
            offset=offset,
        )
        if not results:
            return "No change requests found matching your search."
        return f"Found {len(results)} change request(s):\n{_pretty(results)}"
    except ServiceNowAPIError as e:
        return f"Error searching change requests: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: Add Work Note ────────────────────────────────────────────────

@mcp.tool()
async def add_work_note(identifier: str, note: str) -> str:
    """Add a work note to a ServiceNow change request.

    Args:
        identifier: The change request number (e.g. "CHG0012345") or sys_id.
        note: The work note text to add.
    """
    try:
        result = await _get_client().add_work_note(identifier, note)
        return f"Work note added successfully to {identifier}:\n{_pretty(result)}"
    except ServiceNowAPIError as e:
        return f"Error adding work note: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Tool: Get Approval Status ──────────────────────────────────────────

@mcp.tool()
async def get_approval_status(identifier: str) -> str:
    """Get the approval status and approver details for a ServiceNow change request.

    Args:
        identifier: The change request number (e.g. "CHG0012345") or sys_id.
    """
    try:
        result = await _get_client().get_approval_status(identifier)
        return _pretty(result)
    except ServiceNowAPIError as e:
        return f"Error getting approval status: {e.detail} (HTTP {e.status_code})"
    except Exception as e:
        return f"Error: {e}"


# ── Entrypoint ─────────────────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
