import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent.executor import run_agent
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.workspace_widget import WorkspaceWidget
from app.schemas.agent import (
    ChatRequest,
    ConversationDetail,
    ConversationRead,
    PinWidgetRequest,
    ReorderRequest,
    WorkspaceWidgetRead,
)

router = APIRouter(tags=["agent"])


@router.post("/businesses/{business_id}/agent/chat")
async def agent_chat(
    business_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    async def generate():
        async for chunk in run_agent(
            business_id=business_id,
            user_id=current_user.id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            db=db,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/businesses/{business_id}/agent/workspace",
    response_model=list[WorkspaceWidgetRead],
)
def list_workspace(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == current_user.id,
        )
        .order_by(WorkspaceWidget.position)
        .all()
    )


@router.post(
    "/businesses/{business_id}/agent/workspace",
    status_code=201,
    response_model=WorkspaceWidgetRead,
)
def create_workspace_widget(
    business_id: uuid.UUID,
    payload: PinWidgetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_count = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == current_user.id,
        )
        .count()
    )
    widget = WorkspaceWidget(
        id=uuid.uuid4(),
        business_id=business_id,
        user_id=current_user.id,
        widget_type=payload.widget_type,
        title=payload.title,
        data=payload.data,
        position=payload.position if payload.position is not None else existing_count,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return widget


@router.patch("/businesses/{business_id}/agent/workspace/reorder", status_code=204)
def reorder_widgets(
    business_id: uuid.UUID,
    payload: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for position, widget_id in enumerate(payload.widget_ids):
        db.query(WorkspaceWidget).filter(
            WorkspaceWidget.id == widget_id,
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == current_user.id,
        ).update({"position": position})
    db.commit()


@router.delete("/businesses/{business_id}/agent/workspace/{widget_id}", status_code=204)
def delete_widget(
    business_id: uuid.UUID,
    widget_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    widget = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.id == widget_id,
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == current_user.id,
        )
        .first()
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found.")
    db.delete(widget)
    db.commit()


@router.get(
    "/businesses/{business_id}/agent/conversations",
    response_model=list[ConversationRead],
)
def list_conversations(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.conversation import Conversation

    return (
        db.query(Conversation)
        .filter(
            Conversation.business_id == business_id,
            Conversation.user_id == current_user.id,
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.get(
    "/businesses/{business_id}/agent/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.conversation import Conversation

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.business_id == business_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation
