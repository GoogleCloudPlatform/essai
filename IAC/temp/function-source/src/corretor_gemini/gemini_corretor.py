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

from promptweaver.clients.gemini.gemini_client import GeminiClient
from promptweaver.core.prompt_template import PromptConfig
from config import settings
import pandas as pd
import numpy as np
import json
import os
from typing import Optional
from promptweaver.core.prompt_template import PromptConfig
from promptweaver.clients.gemini.gemini_client import GeminiClient
from sqlalchemy import text 
from src.corretor_gemini.utils import (nota_enem_para_estado,
                                       calcular_nota_competencia,
                                       agregar_descricoes)

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
    
    def get_nota_estado(self):
        """
        Calcula a nota da redação em relação ao estado do Paraná.
        
        Returns:
            int: Nota da redação em relação ao estado do Paraná.
        """
        return nota_enem_para_estado(self.get_nota_enem())

    def get_comentarios(self):
        """
        Agrega os comentários de cada competência da redação.
        
        Returns:
            str: Comentários da redação.
        """
        soma_notas = self.get_nota_enem()
        descricoes = "\n".join(self.correcao_df.apply(lambda row: agregar_descricoes(row), axis=0).to_list())
        descricoes = f"## Nota Total:    \n<strong>ENEM:</strong> {soma_notas}/800 &emsp; | &emsp; <strong>Paraná:</strong> {nota_enem_para_estado(soma_notas)}/60  \n\n ## O que a IA levou em conta para trazer esse feedback? \n\n{descricoes} "
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
            "nota_estado": self.get_nota_estado(),
            "comentarios": self.get_comentarios(),
            "sumarizacao": self.sumarizacao
        }



class Corretor():
    """
    Classe corretor, ajuda a definir o que será necesspario para corrigir uma redação junto com o promptweaver.
    """
    def __init__(self, 
                caminho_prompweaver_corretor : str = settings.PROMPT_CORRECAO,
                caminho_prompweaver_sintetizador: str = settings.PROMPT_SUMARIZACAO,
                config_prompweaver_justificativa: str = settings.PROMPT_VALIDACAO
                ):
        self.gemini_client = GeminiClient(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        self.config_prompweaver_corretor = caminho_prompweaver_corretor
        self.config_prompweaver_sintetizador = caminho_prompweaver_sintetizador
        self.config_prompweaver_justificativa = config_prompweaver_justificativa
        
    
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

        prompt_promptweaver = PromptConfig.from_file(self.config_prompweaver_corretor, redacao_data)
        generate_content = self.gemini_client.generate_content(prompt_promptweaver).text
        
        correcao = Correcao(redacao_data, generate_content)
        correcao.sumarizacao = self.sintetizar_correcao(redacao_data, correcao)

        while correcao.get_nota_enem() > 800:
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
    
    def validate_essay(
                        self,
                        redacao_data,
                        verbose: bool = False
                    ) -> Optional[str]:

        """
        Evaluates the validity of an essay using Gemini.

        Args:
            tema_redacao (str): The theme of the essay.
            enunciado_redacao (str): The essay prompt or statement.
            textos_motivadores (str): The motivational texts.
            redacao_estudante (str): The student's essay text.
            gemini_client (GeminiClient): The Gemini client from PromptWeaver module.
            prompt_template_path (str, optional): Path to the prompt template file.
                Defaults to "Prompts/template-validacao-enem.yml.j2".
            verbose (bool, optional): If True, prints verbose output. Defaults to False.

        Returns:
            Optional[str]: The result of the validation ("Válida" or a message indicating invalidity),
                or None if an error occurs.

        Notes:
            The validation output is an optional enum, with one of the following values:
                - "Válida"
                - "Inválida - Texto Ilegível ou Ininteligível"
                - "Inválida - Desvio do Gênero Dissertativo-Argumentativo"
                - "Inválida - Cópia dos textos motivadores"
                - "Inválida - Violação aos Direitos Humanos"
        """

        # Load the prompt configuration
        try:
            validacao_prompt = PromptConfig.from_file(
                self.config_prompweaver_justificativa, redacao_data, verbose=verbose)
        except Exception as e:
            print(f"Error loading prompt template: {e}")
            return None

        # Generate the content using Gemini
        try:
            response = self.gemini_client.generate_content(validacao_prompt)
            if verbose:
                    print(f"Response from the Gemini model: {response}")
            if hasattr(response, 'text'):
                return response.text
            else:
                print("Invalid response from the Gemini model.")
                return None
        except Exception as e:
            print(f"Error connecting to the Gemini model: {e}")
            return None

    