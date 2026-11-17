# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
from fastapi import APIRouter, Depends, HTTPException

from app import schemas, crud
from app.auth import CallerIdentity, get_current_caller
from app.config import get_settings
from app.security import enforce_caller_rate_limit


router = APIRouter(
    dependencies=[
        Depends(get_current_caller),
        Depends(enforce_caller_rate_limit),
    ]
)


@router.post(
    "/grade",
    status_code=201,
    response_model=schemas.GradingSubmitionSchema,
    tags=["inbound"],
)
async def submit_essay(
    payload: schemas.InboundSchema,
    caller: CallerIdentity = Depends(get_current_caller),
):
    requisicao = crud.create_requisicao(payload, owner_id=caller.subject)
    crud.submit_to_queue(requisicao)

    return schemas.GradingSubmitionSchema(id=requisicao.id)


@router.post(
    "/feedback",
    tags=["inbound"],
)
async def submit_feedback(
    payload: schemas.FeedbackSubmissionSchema,
    caller: CallerIdentity = Depends(get_current_caller),
):
    feedback_id = crud.create_feedback(payload, owner_id=caller.subject)
    return {"id": feedback_id, "status": "success"}


@router.get(
    "/grade/{id}",
    responses={
        200: {"model": schemas.OutboundSchema},
        202: {"model": schemas.InProgress},
        401: {"description": "Não autenticado"},
        403: {"description": "Não autorizado"},
        404: {"description": "Correção não encontrada"},
    },
    tags=["outbound"],
)
async def get_correcao_by_id(
    id: uuid.UUID,
    caller: CallerIdentity = Depends(get_current_caller),
):
    resposta = crud.get_correcao(id, owner_id=caller.subject)

    return resposta


@router.post(
    "/grade/bulk",
    response_model=schemas.BulkSchema,
    tags=["outbound"],
)
async def get_bulk_correcao(
    id_list: list[uuid.UUID],
    caller: CallerIdentity = Depends(get_current_caller),
):
    settings = get_settings()
    if len(id_list) > settings.MAX_IDS_BULK_READ:
        raise HTTPException(
            status_code=400,
            detail=f"Too many ids; current max is {settings.MAX_IDS_BULK_READ}",
        )

    results = crud.get_correcao_bulk(id_list, owner_id=caller.subject)

    return results
