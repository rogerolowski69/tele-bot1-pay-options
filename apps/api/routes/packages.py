from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import PackageModel
from apps.api.db.session import get_db

router = APIRouter(prefix="/api", tags=["packages"])


class PackageResponse(BaseModel):
    id: str
    title: str
    description: str
    amount_minor: int
    currency: str
    is_digital: bool


@router.get("/packages", response_model=list[PackageResponse])
async def list_packages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PackageModel).where(PackageModel.active.is_(True)))
    packages = result.scalars().all()
    return [
        PackageResponse(
            id=p.id,
            title=p.title,
            description=p.description,
            amount_minor=p.amount_minor,
            currency=p.currency,
            is_digital=p.is_digital,
        )
        for p in packages
    ]
