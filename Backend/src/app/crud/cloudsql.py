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

from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.database import engine
from app import models, schemas


def create_requisicao(data: schemas.InboundSchema) -> schemas.InProgress:
    """cria nova requisicao no banco"""
    req = models.Requisicao(**data.model_dump())

    with Session(bind=engine) as session:
        session.add(req)
        session.commit()
        session.refresh(req)

    return schemas.InProgress(id=str(req.id))


def create_feedback(
    data: schemas.FeedbackSubmissionSchema,
) -> schemas.FeedbackSubmissionSchema:
    """cria novo feedback no banco"""
    feedback_raw = feedback_mapper(data)
    feedback = models.Feedback(**feedback_raw)

    with Session(bind=engine) as session:
        # validação
        if (
            session.exec(
                select(models.Correcao).where(
                    models.Correcao.id_requisicao == feedback.idRequisicao
                )
            ).first()
        ) is None:
            raise HTTPException(
                status_code=404,
                detail="Id não encontrado",
            )

        # write
        session.add(feedback)
        session.commit()
        session.refresh(feedback)

    return feedback.id


def feedback_mapper(data: schemas.FeedbackSubmissionSchema):
    feedback = {
        "idProfessor": data.idProfessor,
        "idRequisicao": data.idCorrecao,
        "competencia_1_nota": data.competencia_1.nota,
        "competencia_1_justificativa": data.competencia_1.justificativa,
        "competencia_1_is_modified": data.competencia_1.IsModified,
        "competencia_2_nota": data.competencia_2.nota,
        "competencia_2_justificativa": data.competencia_2.justificativa,
        "competencia_2_is_modified": data.competencia_2.IsModified,
        "competencia_3_nota": data.competencia_3.nota,
        "competencia_3_justificativa": data.competencia_3.justificativa,
        "competencia_3_is_modified": data.competencia_3.IsModified,
        "competencia_4_nota": data.competencia_4.nota,
        "competencia_4_justificativa": data.competencia_4.justificativa,
        "competencia_4_is_modified": data.competencia_4.IsModified,
        "competencia_5_nota": data.competencia_5.nota,
        "competencia_5_justificativa": data.competencia_5.justificativa,
        "competencia_5_is_modified": data.competencia_5.IsModified,
        "justificativa_final_nota": data.justificativa_final.nota,
        "justificativa_final_justificativa": data.justificativa_final.justificativa,
        "justificativa_final_is_modified": data.justificativa_final.IsModified,
        "nota_avaliacao_ia": data.nota_avaliacao_ia,
        "feedback_geral_ia": data.feedback_geral_ia,
    }
    return feedback


def get_correcao(id: uuid.UUID):
    """get correcao from id"""

    with Session(bind=engine) as session:
        if (
            correcao := session.exec(
                select(models.Correcao).where(models.Correcao.id_requisicao == id)
            ).first()
        ) is not None:
            return correcao.format_outbound()
        elif (
            requisicao := session.exec(
                select(models.Requisicao).where(models.Requisicao.id == id)
            ).first()
        ) is not None:
            return schemas.InProgress(id=id)

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


def get_correcao_bulk(data: list[uuid.UUID]):
    correcoes = []
    erros = []

    for id in data:
        try:
            result = get_correcao(id=id)
            correcoes.append(result)
        except Exception as e:
            erros.append(schemas.ErrorSchema(id=id, error_message=str(e)))

    return schemas.BulkSchema(correcoes=correcoes, erros=erros)
