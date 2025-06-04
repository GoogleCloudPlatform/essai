import vertexai
from vertexai.preview.generative_models import GenerativeModel
import json
import os
import re
import pandas as pd
from typing import Dict, Any
from google import genai
from google.genai import types as genai_types

from corretor_gemini.utils.helpers import *

class Correcao:
    """ (Mantido igual ao original) """
    def __init__(self, redacao_data, correcao_response, sumarizacao=None, ignore_json=False):
        self.redacao_data = redacao_data
        self.correcao_response = correcao_response
        if ignore_json:
            self.correcao_data = correcao_response
        else:
            self.correcao_data =  json.loads(correcao_response)
            with open('output_teste.json', 'w') as f:
                json.dump(self.correcao_data, f, indent=2)
                
            #self.correcao_df = pd.DataFrame(self.correcao_data)
            self.correcao_df = pd.DataFrame([])
            self.sumarizacao = sumarizacao
        self.ignore_json = ignore_json

    def get_nota_comptencias(self):
        return self.correcao_df.apply(calcular_nota_competencia, axis=0).T

    def get_nota_enem(self):
        return self.get_nota_comptencias().sum()
    
    def get_comentarios(self):
        if self.ignore_json:
            return self.correcao_response
        try:
            descricoes = "\n".join(self.correcao_df.apply(agregar_descricoes, axis=0).to_list())
            return f"## Nota Total: {self.get_nota_enem()}/1000\n\n{descricoes}"
        except Exception as e:
            return ""

    def get_resposta_completa(self):
        return self.correcao_data
    #return {
            #**self.redacao_data,
            #**self.correcao_data,
            # "nota_enem": self.get_nota_enem(),
            # "comentarios": self.get_comentarios(),
            # "sumarizacao": self.sumarizacao
     #   }

class Corretor:
    def __init__(self,
                 caminho_prompts: str = "Prompts",
                 project: str = None,
                 dummy: bool = False,
                 ignore_json: bool = False,
                 corretor_path : str = None):
        
        vertexai.init(project=project, location="us-central1")
        ##
        ##
        ## Mudar o API Key
        ##
        ##
        ##
        self.client = genai.Client(api_key='AIzaSyBq_1f0_Wz82ydH7ByzXablCDJEVT-jcbA')
    
        self.caminhos = {
            'corretor': {
                'system_prompt': os.path.join(caminho_prompts, corretor_path, 'correcao_system_instruct.txt'),
                'prompt': os.path.join(caminho_prompts, corretor_path, 'correcao.txt'),
                'schema': os.path.join(caminho_prompts, corretor_path, 'correcao_schema.json'),
                'config': os.path.join(caminho_prompts, corretor_path, 'correcao_config.json')
            },
            'sumarizador': {
                'prompt': os.path.join(caminho_prompts, 'Sumarizador' ,'sumarizacao.txt'),
                'schema': os.path.join(caminho_prompts, 'Sumarizador' ,'sumarizacao_schema.json'),
                'config': os.path.join(caminho_prompts, 'Sumarizador' ,'sumarizacao_config.json')
            },
            'invalida': {
                'prompt': os.path.join(caminho_prompts, 'Invalida' , 'invalida.txt'),
                'schema': os.path.join(caminho_prompts, 'Invalida' , 'invalida_schema.json'),
                'config': os.path.join(caminho_prompts, 'Invalida' , 'invalida_config.json')
            }
        }
        
        self.dummy = dummy
        self.ignore_json = ignore_json

    def _carregar_configuracao(self, tipo: str) -> Dict[str, Any]:
        with open(self.caminhos[tipo]['config']) as f:
            config =  json.load(f)
        
        with open(self.caminhos[tipo]['schema']) as f:
            schema = json.load(f)
        
        config['response_schema'] = schema
        #print('CONFIG:', config, end="\n\n" + "-"*50 + "\n\n")
        return config
        

    def _construir_prompt(self, tipo: str, dados: Dict) -> str:
        with open(self.caminhos[tipo]['prompt'], encoding='utf8') as f:
            prompt_template = f.read()
        # Substitui os placeholders no template pelos valores de `dados`
        prompt = prompt_template.format(
            **dados
        )
        #print('Dados:', dados, end="\n\n" + "-"*50 + "\n\n")
        #print('PROMPT FORMATADO:', prompt, end="\n\n" + "-"*50 + "\n\n")
        return prompt
    
    def _construir_system_prompt(self, tipo: str) -> str:
        """
        A função imita _construir_prompt, mas como é system prompt, não precisa da variável dados.
        """
        if 'system_prompt' not in list(self.caminhos[tipo].keys()):
            return None
        
        if not os.path.exists(self.caminhos[tipo]['system_prompt']):
            return None
        
        with open(self.caminhos[tipo]['system_prompt'], encoding='utf8', mode='rt') as f:
            system_prompt = f.read()
        return system_prompt

    def _gerar_resposta(self, prompt: str, config: Dict, system_prompt: str = None) -> str:
        response = self.client.models.generate_content(
            contents=prompt,
            model=config['model_name'],
            config=genai_types.GenerateContentConfig(
                temperature=config['temperature'],
                response_mime_type="application/json",
                response_schema=config['response_schema'],
                system_instruction=system_prompt
            )
        )
        return self._extrair_json(response.text)


    def _extrair_json(self, text: str) -> str:
        # Implemente a lógica para extrair o JSON da resposta, se necessário
        return text

    def get_correcao_from_redacao(self, redacao_data: Dict) -> Correcao:
        if len(redacao_data["redacao_estudante"]) < 150:
            tipo = 'invalida'
        else:
            tipo = 'corretor'
        config = self._carregar_configuracao(tipo)
        prompt = self._construir_prompt(tipo, redacao_data)
        sys_prompt = self._construir_system_prompt(tipo)
        
        if self.dummy:
            return Correcao(redacao_data, "Resposta dummy", ignore_json=True)

        resposta = self._gerar_resposta(prompt, config, sys_prompt)
        try:
            correcao = Correcao(redacao_data, resposta, ignore_json=self.ignore_json)
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {resposta}", end="\n\n" + "-"*50 + "\n\n") 
            print(f"Prompt: {prompt}", end="\n\n" + "-"*50 + "\n\n")
            raise e
        if not self.ignore_json:
            correcao.sumarizacao = self._gerar_sumarizacao(redacao_data, correcao)
            #while correcao.get_nota_enem() > 1000:
            #    resposta = self._gerar_resposta(prompt, config)
            #    correcao = Correcao(redacao_data, resposta, ignore_json=self.ignore_json)
            #    correcao.sumarizacao = self._gerar_sumarizacao(redacao_data, correcao)

        return correcao

    def _gerar_sumarizacao(self, redacao_data: Dict, correcao: Correcao) -> str:
        try:
            dados_sumarizacao = {
                **redacao_data,
                "correcao_redacao": correcao.get_comentarios().replace("\n", "")
            }
            
            config = self._carregar_configuracao('sumarizador')
            prompt = self._construir_prompt('sumarizador', dados_sumarizacao)
            
            return self._gerar_resposta(prompt, config)
        except Exception as e:
            return ""