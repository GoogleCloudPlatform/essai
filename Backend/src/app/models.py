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

from functools import partial
import datetime
import json
import uuid

from sqlmodel import SQLModel, Field, Relationship

from app import schemas


TS_NOW = partial(datetime.datetime.now, tz=datetime.UTC)


class Requisicao(SQLModel, table=True):
    __tablename__ = "requisicao"
    id: uuid.UUID | None = Field(
        primary_key=True,
        index=True,
        default_factory=uuid.uuid4,
    )
    status: str = "inProgress"
    created_at: datetime.datetime = Field(default_factory=TS_NOW)
    updated_at: datetime.datetime = Field(
        default_factory=TS_NOW,
        sa_column_kwargs={"onupdate": TS_NOW},
    )
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

    correcoes: "Correcao" = Relationship(back_populates="requisicao")
    feedback: "Feedback" = Relationship(back_populates="requisicao")


class Correcao(SQLModel, table=True):
    __tablename__ = "correcoes"
    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    id_requisicao: uuid.UUID = Field(foreign_key="requisicao.id")

    started_at: datetime.datetime
    finished_at: datetime.datetime = Field(default_factory=TS_NOW)

    competencia_2_nota: int
    competencia_2_justificativa: str | None
    competencia_3_nota: int
    competencia_3_justificativa: str | None
    competencia_4_nota: int
    competencia_4_justificativa: str | None
    competencia_5_nota: int
    competencia_5_justificativa: str | None

    justificativa_final_nota: int
    justificativa_final_justificativa: str | None

    status: str = "DONE"

    Plagio: str | None
    Validacao: str

    requisicao: Requisicao = Relationship(back_populates="correcoes")

    def format_outbound(self) -> schemas.OutboundSchema:
        def unnest_justificativa_object(justificativa_str):
            """helper function to transform justificativas as objects to NL"""
            try:
                justficativa_as_dict: dict = json.loads(justificativa_str)
                return "\n".join(justficativa_as_dict.values())
            except Exception as e:
                return justificativa_str

        return schemas.OutboundSchema(
            id=self.id_requisicao,
            criteria_2=schemas.CriteriaGrading(
                grade=self.competencia_2_nota,
                reason=unnest_justificativa_object(self.competencia_2_justificativa),
            ),
            criteria_3=schemas.CriteriaGrading(
                grade=self.competencia_3_nota,
                reason=unnest_justificativa_object(self.competencia_3_justificativa),
            ),
            criteria_4=schemas.CriteriaGrading(
                grade=self.competencia_4_nota,
                reason=unnest_justificativa_object(self.competencia_4_justificativa),
            ),
            criteria_5=schemas.CriteriaGrading(
                grade=self.competencia_5_nota,
                reason=unnest_justificativa_object(self.competencia_5_justificativa),
            ),
            final_reason=schemas.CriteriaGrading(
                grade=sum(
                    (
                        self.competencia_2_nota,
                        self.competencia_3_nota,
                        self.competencia_4_nota,
                        self.competencia_5_nota,
                    )
                ),
                reason=unnest_justificativa_object(
                    self.justificativa_final_justificativa
                ),
            ),
            status=self.status,
            Plagio=self.Plagio,
            Validacao=self.Validacao,
        )


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4,
    )
    received_at: datetime.datetime = Field(default_factory=TS_NOW)

    idProfessor: str
    idRequisicao: uuid.UUID = Field(foreign_key="requisicao.id")

    competencia_1_nota: str
    competencia_1_justificativa: str | None
    competencia_1_is_modified: bool = False
    competencia_2_nota: str
    competencia_2_justificativa: str | None
    competencia_2_is_modified: bool = False
    competencia_3_nota: str
    competencia_3_justificativa: str | None
    competencia_3_is_modified: bool = False
    competencia_4_nota: str
    competencia_4_justificativa: str | None
    competencia_4_is_modified: bool = False
    competencia_5_nota: str
    competencia_5_justificativa: str | None
    competencia_5_is_modified: bool = False

    justificativa_final_nota: int
    justificativa_final_justificativa: str | None
    justificativa_final_is_modified: bool = False

    nota_avaliacao_ia: int
    feedback_geral_ia: str

    requisicao: Requisicao = Relationship(back_populates="feedback")
