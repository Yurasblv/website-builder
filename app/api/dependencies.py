from typing import Annotated

from fastapi import Depends

from app.services.generation.pbn import PBNExtraPageGenerator, PBNPagesGenerator, PBNRefreshGenerator
from app.utils import ABCUnitOfWork, UnitOfWork

UnitOfWorkDep = Annotated[ABCUnitOfWork, Depends(UnitOfWork)]
PBNPagesGeneratorDep = Annotated[PBNPagesGenerator, Depends(PBNPagesGenerator._init)]
PBNRefreshGeneratorDep = Annotated[PBNRefreshGenerator, Depends(PBNRefreshGenerator._init)]
PBNExtraPageGeneratorDep = Annotated[PBNExtraPageGenerator, Depends(PBNExtraPageGenerator._init)]
