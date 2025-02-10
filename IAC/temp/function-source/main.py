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

import base64
import functions_framework
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src import DatabaseConnector
from src.models import Requisicao
from src.corretor_gemini import Correcao, Corretor
from src.corretor_gemini.utils.imageUploader import ImageUploader
from uuid import UUID
import json
from datetime import datetime
import pytz
import re

@functions_framework.cloud_event
def handler(cloud_event):
    # Decodifica a mensagem do Pub/Sub
    message_data = cloud_event.data["message"]["data"]
    decoded_message = base64.b64decode(message_data).decode('utf-8')

    print(f"id recebido: {decoded_message}")

    session = None  # Inicialize a variável session
    try:
        # Converte decoded_message para UUID
        uuid_param = UUID(decoded_message)

        # Instancia o conector do banco de dados
        db_connector = DatabaseConnector()

        # Cria a sessão usando o método create_session da classe DatabaseConnector
        session = db_connector.create_session()

        # Imprime o Schema
        db_connector.imprimir_schema()

        # Consulta o banco de dados
        query = select(Requisicao).where(Requisicao.id == uuid_param)
        result = session.execute(query).scalars().first()

        if result:
            # Baixa imagens do drive e sobe para bucket
            reg_links = r"https://drive\.google\.com/file/d/[^/]+\/view\?usp=sharing"
            links_no_texto = re.findall(reg_links, result.TextosMotivadores)

            images = []
            for link in links_no_texto:
                img = ImageUploader(link)
                if not getattr(img, "fail", False):
                    images.append(img)

            texto_adaptado = result.TextosMotivadores
            for img in images:
                texto_adaptado.replace(img.url_original, img.url_cloudstorage)


            # Instancia o Corretor
            corretor = Corretor()
            corrigido_validado = False
            while not corrigido_validado:
                # Monta o dicionário redacao_data com os dados da redação
                redacao_data = {
                    "tema_redacao": result.TitleTema,
                    "enunciado_redacao": result.DescricaoPedido,
                    "textos_motivadores": texto_adaptado.replace("\n", "").replace("\r", ""),
                    "redacao_estudante": result.Redacao.replace("\n", "").replace("\r", "")
                }

                # Realiza a correção com o dicionário redacao_data
                datetime_inicio_correcao = datetime.now(pytz.timezone("America/Sao_Paulo"))
                # Aplica a Correção na redação.
                correcao = corretor.get_correcao_from_redacao(redacao_data)
                # Aplica a Validação.
                validacao = corretor.validate_essay(redacao_data)

                # Extrai dados da correção
                resultado = correcao.get_resposta_completa()
                comentarios = correcao.get_comentarios()
                notas_competencias = correcao.get_nota_comptencias()
                nota_enem = correcao.get_nota_enem()
               

                print(resultado)
                # Competências esperadas
                competencias = ["competencia_2", "competencia_3", "competencia_4", "competencia_5"]
                
                # Validação Esperada.
                validacao_enum = [
                                    'Válida', 
                                    'Inválida - Texto Ilegível ou Ininteligível', 
                                    'Inválida - Desvio do Gênero Dissertativo-Argumentativo', 
                                    'Inválida - Cópia dos textos motivadores', 
                                    'Inválida - Violação aos Direitos Humanos'
                                ]


                notas_compt = []
                corrigido_validado = True
                # Loop para verificar cada competência e extrair o valor
                for competencia in competencias:
                    if competencia in notas_competencias:
                        notas_compt.append(notas_competencias[competencia])
                    else:
                        corrigido_validado = False
                        notas_compt = []  # Limpa a lista de valores, pois não está corrigido
                        break

                if validacao not in validacao_enum: 
                    corrigido_validado = False

                print("Correção realizada:", resultado, validacao)

                # Salva a correção no banco de dados se `corrigido` for True
                if corrigido_validado:
                    db_connector.salvar_correcao(
                        id_requisicao=uuid_param,
                        resultado=resultado,
                        validacao=validacao,
                        nota_enem=nota_enem,
                        notas_competencias=notas_compt,
                        datetime_inicio_correcao=datetime_inicio_correcao,
                        plagio=correcao.plagio if hasattr(correcao, 'plagio') else None,
                    )

                else:
                    print("Correção incompleta, tentando novamente.")

        else:
            print(f"Nenhum dado encontrado para o UUID: {decoded_message}")

    except Exception as e:
        print(f"Erro ao buscar dados: {e}")

    finally:
        if session:
            session.close()
