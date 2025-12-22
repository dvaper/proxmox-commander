"""
Executions Router - Ansible/Terraform Ausführungen

Berechtigungsfilterung:
- Super-Admins sehen alle Executions
- Reguläre User sehen nur eigene Executions
- Ansible-Ausführung: Playbook und Gruppen müssen zugänglich sein
"""
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.models.execution import Execution
from app.schemas.execution import (
    ExecutionResponse,
    ExecutionListResponse,
    AnsibleExecutionCreate,
    TerraformExecutionCreate,
)
from app.services.ansible_service import AnsibleService
from app.services.terraform_service import TerraformService
from app.services.permission_service import get_permission_service

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    page: int = 1,
    page_size: int = 20,
    execution_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Liste der Executions (paginiert).

    Gefiltert nach Berechtigungen:
    - Super-Admin: Alle Executions
    - Regulärer User: Nur eigene Executions
    """
    perm_service = get_permission_service(current_user)

    # Basis-Query
    query = select(Execution)
    count_query = select(func.count()).select_from(Execution)

    # Berechtigungsfilter: Nur eigene Executions (außer Super-Admin)
    user_filter_id = perm_service.get_execution_filter_user_id()
    if user_filter_id is not None:
        query = query.where(Execution.user_id == user_filter_id)
        count_query = count_query.where(Execution.user_id == user_filter_id)

    # Typ-Filter
    if execution_type:
        query = query.where(Execution.execution_type == execution_type)
        count_query = count_query.where(Execution.execution_type == execution_type)

    # Status-Filter
    if status:
        query = query.where(Execution.status == status)
        count_query = count_query.where(Execution.status == status)

    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    query = query.order_by(desc(Execution.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    executions = result.scalars().all()

    return ExecutionListResponse(
        items=executions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Einzelne Execution mit Details (mit Berechtigungsprüfung)"""
    perm_service = get_permission_service(current_user)

    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution nicht gefunden")

    # Berechtigungsprüfung
    if not perm_service.can_view_execution(execution.user_id):
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Execution")

    return execution


@router.post("/ansible", response_model=ExecutionResponse)
async def run_ansible(
    data: AnsibleExecutionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ansible Playbook ausführen.

    Berechtigungsprüfung:
    - Playbook muss zugänglich sein
    - Alle Ziel-Gruppen müssen zugänglich sein
    """
    perm_service = get_permission_service(current_user)

    # Berechtigungsprüfung (wenn nicht Super-Admin)
    if not perm_service.is_super_admin:
        # Playbook-Berechtigung prüfen
        if not perm_service.can_access_playbook(data.playbook_name):
            raise HTTPException(
                status_code=403,
                detail=f"Keine Berechtigung für Playbook '{data.playbook_name}'",
            )

        # Gruppen-Berechtigung prüfen
        target_groups = data.target_groups or []
        if target_groups:
            accessible_groups = perm_service.get_accessible_groups()
            for group in target_groups:
                if group not in accessible_groups:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Keine Berechtigung für Gruppe '{group}'",
                    )

    # Execution erstellen
    execution = Execution(
        execution_type="ansible",
        status="pending",
        playbook_name=data.playbook_name,
        target_hosts=json.dumps(data.target_hosts) if data.target_hosts else None,
        target_groups=json.dumps(data.target_groups) if data.target_groups else None,
        extra_vars=json.dumps(data.extra_vars) if data.extra_vars else None,
        user_id=current_user.id,
    )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Ansible im Hintergrund starten
    ansible_service = AnsibleService()
    background_tasks.add_task(
        ansible_service.run_playbook,
        execution_id=execution.id,
        playbook_name=data.playbook_name,
        target_hosts=data.target_hosts,
        target_groups=data.target_groups,
        extra_vars=data.extra_vars,
    )

    return execution


@router.post("/terraform", response_model=ExecutionResponse)
async def run_terraform(
    data: TerraformExecutionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Terraform Operation ausführen.

    Hinweis: Terraform-Berechtigungen werden derzeit nicht eingeschränkt.
    """
    # Execution erstellen
    execution = Execution(
        execution_type="terraform",
        status="pending",
        tf_action=data.tf_action,
        tf_module=data.tf_module,
        tf_vars=json.dumps(data.tf_vars) if data.tf_vars else None,
        user_id=current_user.id,
    )

    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Terraform im Hintergrund starten
    terraform_service = TerraformService()
    background_tasks.add_task(
        terraform_service.run_action,
        execution_id=execution.id,
        action=data.tf_action,
        module=data.tf_module,
        variables=data.tf_vars,
    )

    return execution


@router.delete("/{execution_id}")
async def delete_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execution löschen (mit Berechtigungsprüfung).

    - Laufende Executions werden erst abgebrochen, dann gelöscht
    - Nur eigene Executions oder als Super-Admin
    """
    perm_service = get_permission_service(current_user)

    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution nicht gefunden")

    # Berechtigungsprüfung
    if not perm_service.can_view_execution(execution.user_id):
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Löschen dieser Execution")

    # Laufende Execution erst abbrechen
    if execution.status in ["pending", "running"]:
        execution.status = "cancelled"
        await db.commit()

    # Zugehörige Logs löschen
    from app.models.execution_log import ExecutionLog
    await db.execute(
        select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
    )

    # Execution löschen
    await db.delete(execution)
    await db.commit()

    return {"message": "Execution gelöscht", "id": execution_id}


@router.delete("")
async def delete_all_executions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Alle Executions löschen.

    - Super-Admin: Alle Executions
    - Regulärer User: Nur eigene Executions
    """
    perm_service = get_permission_service(current_user)

    from app.models.execution_log import ExecutionLog
    from sqlalchemy import delete

    # Basis-Filter für Berechtigungen
    user_filter_id = perm_service.get_execution_filter_user_id()

    if user_filter_id is not None:
        # Regulärer User: Nur eigene
        # Erst IDs der zu löschenden Executions holen
        result = await db.execute(
            select(Execution.id).where(Execution.user_id == user_filter_id)
        )
        execution_ids = [row[0] for row in result.fetchall()]

        if execution_ids:
            # Logs löschen
            await db.execute(
                delete(ExecutionLog).where(ExecutionLog.execution_id.in_(execution_ids))
            )
            # Executions löschen
            await db.execute(
                delete(Execution).where(Execution.user_id == user_filter_id)
            )
        count = len(execution_ids)
    else:
        # Super-Admin: Alle
        # Zählen
        count_result = await db.execute(select(func.count()).select_from(Execution))
        count = count_result.scalar()

        # Alle Logs löschen
        await db.execute(delete(ExecutionLog))
        # Alle Executions löschen
        await db.execute(delete(Execution))

    await db.commit()

    return {"message": f"{count} Execution(s) gelöscht", "count": count}
