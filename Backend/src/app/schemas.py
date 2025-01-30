# Copyright 2022 Google LLC
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
from typing import Optional
from pydantic import BaseModel, field_validator, Field
from app import enums


# inbound
class InboundSchema(BaseModel):
    TokenRedacao: str
    DescDependencia: str
    IdMunicipio: str
    DescMunicipio: str
    IdNRE: str
    DescNRE: str
    IdEscola: str
    DescEscola: str
    IdCurso: str
    DescCurso: str
    IdTurma: str
    IdTurno: str
    DescTurno: str
    IdEtapa: str
    DescEtapa: str
    IdSeriacao: str
    DescSeriacao: str
    IdDisciplina: str
    DescDisciplina: str
    IdProfessor: str
    NomeProfessor: str
    IdAluno: str
    IdTema: str
    DescTema: str
    IdTipo: str
    DescricaoTipo: str
    IdGenero: str
    DescricaoGenero: str
    IdProposta: str
    MinPalavras: int
    MaxPalavras: int
    TitleTema: str
    DescricaoPedido: str
    TextosMotivadores: str
    TituloRedacao: str
    Redacao: str


class GradingSubmitionSchema(BaseModel):
    id: uuid.UUID


class CriteriaGrading(BaseModel):
    grade: int
    reason: str | None


class OutboundSchema(BaseModel):
    id: uuid.UUID
    criteria_2: CriteriaGrading
    criteria_3: CriteriaGrading
    criteria_4: CriteriaGrading
    criteria_5: CriteriaGrading

    final_reason: CriteriaGrading
    status: enums.ProcessStatus = enums.ProcessStatus.DONE
    Plagio: str | None
    Validacao: str | None


class InProgress(BaseModel):
    id: uuid.UUID
    status: str = enums.ProcessStatus.NOT_DONE


class ErrorSchema(BaseModel):
    id: uuid.UUID
    error_message: str


class BulkSchema(BaseModel):
    correcoes: list[OutboundSchema | InProgress | None]
    erros: list[ErrorSchema | None]


class GradingCriteriaFeedback(BaseModel):
    nota: int
    justificativa: str | None
    IsModified: bool


class CriteriaFeedbackValidated(GradingCriteriaFeedback):
    @field_validator("nota")
    def validate_nota(cls, v):
        allowed_values = {0, 40, 80, 120, 160, 200}
        if v not in allowed_values:
            raise ValueError(f"Nota deve ser um dos seguintes int: {allowed_values}")
        return v


class FinalReasonFeedback(BaseModel):
    nota: int
    justificativa: str | None
    IsModified: bool


class FeedbackSubmissionSchema(BaseModel):
    idCorrecao: uuid.UUID
    idProfessor: str

    criteria_1: GradingCriteriaFeedback
    criteria_2: CriteriaFeedbackValidated
    criteria_3: CriteriaFeedbackValidated
    criteria_4: CriteriaFeedbackValidated
    criteria_5: CriteriaFeedbackValidated
    final_reason: FinalReasonFeedback

    ai_grading: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        title="AI Grading Evaluation",
        description="Integer between 1 and 10, or None.",
    )

    @field_validator("ai_grading")
    def ia_grading_must_be_int(cls, v):
        if v is not None and not isinstance(v, int):
            raise ValueError("Invalid grade; should be 1 <= int <= 10 ")
        return v

    general_feedback_ia: str | None
