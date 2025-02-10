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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, Integer  
from datetime import datetime
from uuid import uuid4


# Base do modelo
Base = declarative_base()

class Requisicao(Base):
    __tablename__ = 'requisicao'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))  # Gera um UUID automaticamente
    status = Column(String, default='inProgress')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    TokenRedacao = Column(String)
    DescDependencia = Column(String)
    IdMunicipio = Column(String)
    DescMunicipio = Column(String)
    IdNRE = Column(String)
    DescNRE = Column(String)
    IdEscola = Column(String)
    DescEscola = Column(String)
    IdCurso = Column(String)
    DescCurso = Column(String)
    IdTurno = Column(String)
    DescTurno = Column(String)
    IdEtapa = Column(String)
    DescEtapa = Column(String)
    IdSeriacao = Column(String)
    DescSeriacao = Column(String)
    IdDisciplina = Column(String)
    DescDisciplina = Column(String)
    IdProfessor = Column(String)
    NomeProfessor = Column(String)
    IdAluno = Column(String)
    IdTema = Column(String)
    DescTema = Column(String)
    IdTipo = Column(String)
    DescricaoTipo = Column(String)
    IdGenero = Column(String)
    DescricaoGenero = Column(String)
    IdProposta = Column(String)
    MinPalavras = Column(String)  
    MaxPalavras = Column(String)  
    TitleTema = Column(String)
    DescricaoPedido = Column(String)
    TextosMotivadores = Column(String)
    TituloRedacao = Column(String)
    Redacao = Column(String)


class CorrecaoModel(Base):
    __tablename__ = 'correcoes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_requisicao = Column(UUID(as_uuid=True), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True) 
    
    competencia_2_nota = Column(Integer, nullable=False)
    competencia_2_justificativa = Column(String, nullable=True)
    competencia_3_nota = Column(Integer, nullable=False)
    competencia_3_justificativa = Column(String, nullable=True)
    competencia_4_nota = Column(Integer, nullable=False)
    competencia_4_justificativa = Column(String, nullable=True)
    competencia_5_nota = Column(Integer, nullable=False)
    competencia_5_justificativa = Column(String, nullable=True)
    
    justificativa_final_nota = Column(Integer, nullable=False)
    justificativa_final_justificativa = Column(String, nullable=True)
    
    status = Column(String, nullable=False, default='DONE') 
    Plagio = Column(String, nullable=True)
    Validacao = Column(String, nullable=False)
