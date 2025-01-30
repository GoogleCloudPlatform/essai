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

from promptweaver.clients.gemini.gemini_client import GeminiClient
from promptweaver.core.prompt_template import PromptConfig
import pandas as pd
import numpy as np
import json
import os

from corretor_gemini.utils.helpers import *

class Correcao():
    """
    Classe que representa a resposta do corretor, possui as informações da redação, a nota e os comentários.
    """
    def __init__(self, redacao_data, correcao_response, sumarizacao=None):
        self.redacao_data = redacao_data
        self.correcao_data = json.loads(correcao_response)
        self.correcao_df = pd.DataFrame(self.correcao_data)
        self.sumarizacao = sumarizacao

    def get_nota_comptencias(self):
        """
        Calcula a nota de cada competência da redação.
        
        Returns:
            pd.Series: Série com as notas de cada competência.
        """
        nota_competencias = self.correcao_df.apply(calcular_nota_competencia, axis=0)
        nota_competencias = nota_competencias.T
        nota_competencias.columns = ['Competência 2', 'Competência 3', 'Competência 4', 'Competência 5']
        return nota_competencias

    def get_nota_enem(self):
        """
        Calcula a nota total da redação.
        
        Returns:
            int: Nota total da redação.
        """
        return self.get_nota_comptencias().sum()
    
    def get_comentarios(self):
        """
        Agrega os comentários de cada competência da redação.
        
        Returns:
            str: Comentários da redação.
        """
        soma_notas = self.get_nota_enem()
        descricoes = "\n".join(self.correcao_df.apply(lambda row: agregar_descricoes(row), axis=0).to_list())
        descricoes = f"## Nota Total:    \n<strong>ENEM:</strong> {soma_notas}/1000 &emsp; \n\n ## O que a IA levou em conta para trazer esse feedback? \n\n{descricoes} "
        return descricoes

    
    def get_resposta_completa(self):
        """
        Retorna a resposta completa da redação.
        
        Returns:
            dict: Dicionário com a resposta da redação.
        """
        return {
            **self.redacao_data,
            **self.correcao_data,
            "nota_competencias": self.get_nota_comptencias().to_dict(),
            "nota_enem": self.get_nota_enem(),
            "comentarios": self.get_comentarios(),
            "sumarizacao": self.sumarizacao
        }



class Corretor():
    """
    Classe corretor, ajuda a definir o que será necesspario para corrigir uma redação junto com o promptweaver.
    """
    def __init__(self,
                caminho_prompweaver_corretor : str = "../Prompts/template-correcao-enem.yml.j2",
                caminho_prompweaver_sintetizador: str = "../Prompts/template-sumarizacao-enem.yml.j2",
                caminho_prompweaver_corretor_invalida: str = "../Prompts/template-correcao-enem-invalida.yml.j2",
                project: str = None,
                dummy: bool = False):
        self.gemini_client = GeminiClient(project=project, location="us-central1")
        self.config_prompweaver_corretor = caminho_prompweaver_corretor
        self.config_prompweaver_sintetizador = caminho_prompweaver_sintetizador
        ## Adicionado para lidar com casos onde a redação é menor que 150 caracteres
        self.config_prompweaver_corretor_invalida = caminho_prompweaver_corretor_invalida
        ## Fim da adição
        self.dummy = dummy
    
    def get_correcao_from_redacao(self, 
                                  redacao_data: dict) -> dict:
        """
        Executa a correção de uma redação com o Gemini.
        
        Args:
            redacao_data (dict): Dicionário com os dados da redação.
                - tema_redacao (str): Tema da redação.
                - enunciado_redacao (str): Enunciado da redação.
                - textos_motivadores (str): Textos motivadores da redação.
                - redacao_estudante (str): Texto da redação.

        Returns:
            Correcao: Objeto com a resposta do Gemini e helpers para processa-la.
        """
        ## Adicionado para lidar com casos onde a redação é menor que 150 caracteres
        if len(redacao_data["redacao_estudante"]) < 150:
            prompt_promptweaver = PromptConfig.from_file(self.config_prompweaver_corretor_invalida, redacao_data)
        else:
            ## Fim da adição
            prompt_promptweaver = PromptConfig.from_file(self.config_prompweaver_corretor, redacao_data)
        generate_content = self.gemini_client.generate_content(prompt_promptweaver).text

        if self.dummy:
            return generate_content
        
        correcao = Correcao(redacao_data, generate_content)
        correcao.sumarizacao = self.sintetizar_correcao(redacao_data, correcao)

        while correcao.get_nota_enem() > 1000:
            generate_content = self.gemini_client.generate_content(prompt_promptweaver)
            correcao = Correcao(redacao_data,
                                generate_content)
            correcao.sumarizacao = self.sintetizar_correcao(redacao_data, correcao)
        return correcao

    def sintetizar_correcao(self,
                        redacao_data: dict,
                        correcao: Correcao) -> str:
        """
        Sintetiza a correção de uma redação.
        
        Args:
            correcao (Correcao): Objeto com a resposta do Gemini e helpers para processa-la.

        Returns:
            str: Texto com a correção da redação.
        """
        # Remova o ".replace("\n", "").replace("\r", "")" quando o issue do promptweaver for resolvido
        correcao_data = redacao_data | {"correcao_redacao" : correcao.get_comentarios().replace("\n", "").replace("\r", "")}
        
        prompt_promptweaver = PromptConfig.from_file(self.config_prompweaver_sintetizador, correcao_data)
        generate_content = self.gemini_client.generate_content(prompt_promptweaver).text

        return generate_content