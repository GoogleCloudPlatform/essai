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
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from src.models import CorrecaoModel
from google.cloud.sql.connector import Connector, IPTypes
from config import settings
from uuid import uuid4
import pytz
import pg8000
from sqlalchemy import MetaData
from sqlalchemy import text 
import json

class DatabaseConnector:
    def __init__(self):
        # Configurações da instância Cloud SQL e do banco de dados
        self.instance_connection_name = settings.INSTANCE_CONNECTION_NAME
        self.database = settings.DB_DATABASE
        self.iam_user = settings.DB_USER
        self.ip_type = IPTypes.PRIVATE 
        self.connector = Connector(ip_type=self.ip_type)

    def get_engine(self):
        def getconn() -> pg8000.dbapi.Connection:
            # Conecta ao banco de dados Cloud SQL com autenticação IAM
            conn: pg8000.dbapi.Connection = self.connector.connect(
                self.instance_connection_name,
                "pg8000",
                user=self.iam_user,
                db=self.database,
                enable_iam_auth=True,  # Habilita autenticação IAM
                ip_type=self.ip_type
            )
            return conn

        # Cria o pool de conexões com SQLAlchemy
        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,
            pool_recycle=1800  # Recicla a conexão a cada 30 minutos
        )
        return engine

    def create_session(self):
        # Cria uma sessão para interagir com o banco de dados
        engine = self.get_engine()
        Session = sessionmaker(bind=engine)
        return Session()

    def imprimir_schema(self, nome_tabela='correcoes'):
        """
        Imprime o esquema da tabela especificada.

        Args:
            engine: Instância do SQLAlchemy Engine conectada ao banco de dados.
            nome_tabela (str): Nome da tabela a ser inspecionada.
        """
        inspetor = inspect(self.get_engine())
        colunas = inspetor.get_columns(nome_tabela)
        
        print(f"Esquema da tabela '{nome_tabela}':")
        for coluna in colunas:
            nome = coluna['name']
            tipo = coluna['type']
            nullable = coluna['nullable']
            default = coluna.get('default', None)
            print(f"Coluna: {nome}, Tipo: {tipo}, Nulo: {nullable}, Valor Padrão: {default}")
            
    def salvar_correcao(self, id_requisicao, resultado, validacao,
                    nota_enem, notas_competencias, 
                    datetime_inicio_correcao, 
                    plagio=None):
        
        print(f"{id} Salvando")
        #try:
        session = self.create_session()

        # Inicializa a data de término com o timezone
        finished_at = datetime.now(pytz.timezone("America/Sao_Paulo"))

        # Lista de competências para processar dinamicamente
        competencias = ['competencia_2', 'competencia_3', 'competencia_4', 'competencia_5']
        competencia_dados = {}
        
        # Extrai e prepara os dados de cada competência
        for comp in competencias:
            competencia = resultado.get(comp, {})
            competencia_dados[f"{comp}_nota"] = str(competencia.get('notas', ""))
            competencia_dados[f"{comp}_justificativa"] = json.dumps(competencia.get('descricoes', ""))

        # Criação do objeto de correção com dados dinâmicos
        nova_correcao = CorrecaoModel(
            id_requisicao=id_requisicao,
            started_at=datetime_inicio_correcao,
            finished_at=finished_at,

            # Atribui as notas e justificativas de forma dinâmica
            competencia_2_nota=int(notas_competencias[0]),
            competencia_2_justificativa=competencia_dados.get('competencia_2_justificativa'),
            competencia_3_nota=int(notas_competencias[1]),
            competencia_3_justificativa=competencia_dados.get('competencia_3_justificativa'),
            competencia_4_nota=int(notas_competencias[2]),
            competencia_4_justificativa=competencia_dados.get('competencia_4_justificativa'),
            competencia_5_nota=int(notas_competencias[3]),
            competencia_5_justificativa=competencia_dados.get('competencia_5_justificativa'),

            # Justificativa final
            justificativa_final_nota=nota_enem,
            justificativa_final_justificativa=resultado.get('sumarizacao'),

            status="DONE",
            Plagio=plagio,
            Validacao=validacao
        )

        session.add(nova_correcao)
        session.commit()
        print(f"Correção para UUID {id} salva com sucesso.")

        query = select(CorrecaoModel).where(CorrecaoModel.id_requisicao == id_requisicao)
        result = session.execute(query).scalars().first()

        if result:
            print("Resultado", result)

        '''
        except Exception as e:
            logging.error(f"Erro ao salvar correção: {e}")

        finally:
            session.close()'''
