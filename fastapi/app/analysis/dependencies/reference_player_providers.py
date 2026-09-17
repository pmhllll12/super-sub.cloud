"""선수 저장소·유스케이스 프로바이더. `paik` 29번."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analysis.adapter.outbound.pg.reference_player_pg_repository import (
    ReferencePlayerPgRepository,
)
from app.analysis.application.ports.input.reference_player_use_cases import (
    GetReferencePlayerSkeletonUseCase,
    GetVideoSkeletonUseCase,
    ListReferencePlayersUseCase,
)
from app.analysis.application.ports.output.reference_player_port import (
    ReferencePlayerPort,
)
from app.analysis.application.use_cases.reference_player_interactors import (
    GetReferencePlayerSkeletonInteractor,
    GetVideoSkeletonInteractor,
    ListReferencePlayersInteractor,
)
from app.analysis.dependencies.job_providers import JobRepositoryDep
from app.analysis.dependencies.video_providers import StorageDep, VideoRepositoryDep
from app.core.database import get_session


def get_reference_player_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ReferencePlayerPort:
    return ReferencePlayerPgRepository(session)


ReferencePlayerRepositoryDep = Annotated[
    ReferencePlayerPort, Depends(get_reference_player_repository)
]


def get_list_reference_players_use_case(
    repository: ReferencePlayerRepositoryDep,
) -> ListReferencePlayersUseCase:
    return ListReferencePlayersInteractor(repository)


ListReferencePlayersUseCaseDep = Annotated[
    ListReferencePlayersUseCase, Depends(get_list_reference_players_use_case)
]


def get_reference_player_skeleton_use_case(
    repository: ReferencePlayerRepositoryDep, storage: StorageDep
) -> GetReferencePlayerSkeletonUseCase:
    return GetReferencePlayerSkeletonInteractor(repository, storage)


GetReferencePlayerSkeletonUseCaseDep = Annotated[
    GetReferencePlayerSkeletonUseCase,
    Depends(get_reference_player_skeleton_use_case),
]


def get_video_skeleton_use_case(
    video_repository: VideoRepositoryDep,
    job_repository: JobRepositoryDep,
    storage: StorageDep,
) -> GetVideoSkeletonUseCase:
    return GetVideoSkeletonInteractor(video_repository, job_repository, storage)


GetVideoSkeletonUseCaseDep = Annotated[
    GetVideoSkeletonUseCase, Depends(get_video_skeleton_use_case)
]
