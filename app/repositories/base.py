from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Any) -> Optional[ModelType]:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        obj_data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, BaseModel) else obj_in
        for field in obj_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_data[field])
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> Optional[ModelType]:
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
        return obj
