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

import logging
import uuid

from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.database import get_engine
from app import models, schemas

log = logging.getLogger("uvicorn")


def _require_owner_id(owner_id: str) -> str:
    if not isinstance(owner_id, str) or not owner_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing caller identity",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return owner_id.strip()


def create_requisicao(data: schemas.InboundSchema, owner_id: str) -> schemas.InProgress:
    """cria nova requisicao no banco"""
    verified_owner = _require_owner_id(owner_id)
    req = models.Requisicao(**data.model_dump(), owner_id=verified_owner)

    with Session(bind=get_engine()) as session:
        session.add(req)
        session.commit()
        session.refresh(req)

    return schemas.InProgress(id=str(req.id))


def create_feedback(
    data: schemas.FeedbackSubmissionSchema,
    owner_id: str,
) -> uuid.UUID:
    """cria novo feedback no banco"""
    verified_owner = _require_owner_id(owner_id)

    with Session(bind=get_engine()) as session:
        # Enforce both existence and caller ownership close to data access.
        correcao = session.exec(
            select(models.Correcao)
            .join(
                models.Requisicao,
                models.Correcao.id_requisicao == models.Requisicao.id,
            )
            .where(
                models.Correcao.id_requisicao == data.idCorrecao,
                models.Requisicao.owner_id == verified_owner,
            )
        ).first()
        if correcao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Id não encontrado",
            )

        feedback_raw = feedback_mapper(data)
        feedback = models.Feedback(**feedback_raw)

        # write
        session.add(feedback)
        session.commit()
        session.refresh(feedback)

    return feedback.id


def feedback_mapper(data: schemas.FeedbackSubmissionSchema):
    feedback = {
        "idProfessor": data.idProfessor,
        "idRequisicao": data.idCorrecao,
        "competencia_1_nota": str(data.criteria_1.nota),
        "competencia_1_justificativa": data.criteria_1.justificativa,
        "competencia_1_is_modified": data.criteria_1.IsModified,
        "competencia_2_nota": str(data.criteria_2.nota),
        "competencia_2_justificativa": data.criteria_2.justificativa,
        "competencia_2_is_modified": data.criteria_2.IsModified,
        "competencia_3_nota": str(data.criteria_3.nota),
        "competencia_3_justificativa": data.criteria_3.justificativa,
        "competencia_3_is_modified": data.criteria_3.IsModified,
        "competencia_4_nota": str(data.criteria_4.nota),
        "competencia_4_justificativa": data.criteria_4.justificativa,
        "competencia_4_is_modified": data.criteria_4.IsModified,
        "competencia_5_nota": str(data.criteria_5.nota),
        "competencia_5_justificativa": data.criteria_5.justificativa,
        "competencia_5_is_modified": data.criteria_5.IsModified,
        "justificativa_final_nota": data.final_reason.nota,
        "justificativa_final_justificativa": data.final_reason.justificativa,
        "justificativa_final_is_modified": data.final_reason.IsModified,
        "nota_avaliacao_ia": data.ai_grading,
        "feedback_geral_ia": data.general_feedback_ia,
    }
    return feedback


def get_correcao(id: uuid.UUID, owner_id: str):
    """get correcao from id enforcing caller ownership (fail-closed)"""
    verified_owner = _require_owner_id(owner_id)

    with Session(bind=get_engine()) as session:
        # Verify ownership on the parent Requisicao first; rows with a different
        # owner_id or NULL owner_id are denied identically to nonexistent IDs.
        requisicao = session.exec(
            select(models.Requisicao).where(
                models.Requisicao.id == id,
                models.Requisicao.owner_id == verified_owner,
            )
        ).first()
        if requisicao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[
                    {
                        "loc": ["body", str(id)],
                        "msg": "Id não encontrado",
                        "type": "value_error.not_found",
                    }
                ],
            )

        correcao = session.exec(
            select(models.Correcao).where(models.Correcao.id_requisicao == id)
        ).first()
        if correcao is not None:
            return correcao.format_outbound()

        return schemas.InProgress(id=id)


def get_correcao_bulk(data: list[uuid.UUID], owner_id: str):
    verified_owner = _require_owner_id(owner_id)
    correcoes = []
    erros = []

    for id in data:
        try:
            result = get_correcao(id=id, owner_id=verified_owner)
            correcoes.append(result)
        except HTTPException as exc:
            error_msg = (
                "Id não encontrado"
                if exc.status_code == status.HTTP_404_NOT_FOUND
                else "Acesso negado"
            )
            erros.append(schemas.ErrorSchema(id=id, error_message=error_msg))
        except Exception:
            log.exception("Unexpected error fetching grading result for id '%s'", id)
            erros.append(
                schemas.ErrorSchema(id=id, error_message="Erro ao consultar correção")
            )

    return schemas.BulkSchema(correcoes=correcoes, erros=erros)
