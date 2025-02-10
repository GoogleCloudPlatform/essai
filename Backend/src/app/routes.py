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
from fastapi import APIRouter, HTTPException

from app import schemas, crud
from app.config import settings


router = APIRouter()


@router.post(
    "/grade",
    status_code=201,
    response_model=schemas.GradingSubmitionSchema,
    tags=["inbound"],
)
async def submit_essay(
    payload: schemas.InboundSchema,
):
    requisicao = crud.create_requisicao(payload)
    crud.submit_to_queue(requisicao)

    return schemas.GradingSubmitionSchema(id=requisicao.id)


@router.post(
    "/feedback",
    tags=["inbound"],
)
async def submit_feedback(payload: schemas.FeedbackSubmissionSchema):
    feedback_id = crud.create_feedback(payload)
    return {"id": feedback_id, "status": "success"}


@router.get(
    "/grade/{id}",
    responses={
        200: {"model": schemas.OutboundSchema},
        202: {"model": schemas.InProgress},
        404: {"description": "Correção não encontrada"},
    },
    tags=["outbound"],
)
async def get_correcao_by_id(
    id: uuid.UUID,
):
    # correcao_id = schemas.CorrecaoSubmitionSchema(id=id)
    # resposta = crud.get_correcao(correcao_id)
    resposta = crud.get_correcao(id)

    return resposta


@router.post(
    "/grade/bulk",
    response_model=schemas.BulkSchema,
    tags=["outbound"],
)
async def get_bulk_correcao(
    id_list: list[uuid.UUID],
):
    if len(id_list) > settings.MAX_IDS_BULK_READ:
        raise HTTPException(
            status_code=400,
            detail=f"Too many ids; current max is {settings.MAX_IDS_BULK_READ}",
        )

    results = crud.get_correcao_bulk(id_list)

    return results
