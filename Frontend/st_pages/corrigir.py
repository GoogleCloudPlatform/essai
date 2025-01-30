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

from promptweaver.core.prompt_template import PromptConfig
import streamlit as st
import pandas as pd
import numpy as np
import json
import os

from utils.notas import *
from corretor_gemini.gemini_corretor import Corretor

PROVA = 'enem'

corretor = Corretor(f"Prompts//template-correcao-{PROVA}.yml.j2", f"Prompts//template-sumarizacao-{PROVA}.yml.j2",project=os.environ.get('PROJECT_ID'))

competencias = PromptConfig.from_file_with_sample_values(corretor.config_prompweaver_corretor) \
               .generation_config['response_schema']['required']

def on_submit_redacao():
    with st.spinner(f'Wating for the model...'):
        x = {
            "tema_redacao": tema_redacao,
            "textos_motivadores": textos_motivadores,
            "redacao_estudante": redacao_aluno,
            "enunciado_redacao": "",
        }

        correcao = corretor.get_correcao_from_redacao(x)
    
    
    st.markdown(f"# Theme: {tema_redacao}")
    st.expander("Support texts:", expanded=False).markdown(textos_motivadores)
    st.expander("Student Essay", expanded=False).markdown(redacao_aluno)

    if type(notasProfessores) != type(None): 
        st.expander("Assessment by Competency Teachers", expanded=False).write(notasProfessores)
    st.markdown("### Assessment by Competency Teachers")

    notas = correcao.get_nota_comptencias().T
    notas.columns = competencias
    st.write(notas)
    st.markdown(correcao.get_comentarios(), unsafe_allow_html=True)
    st.expander("JSON Model Response", expanded=False).write(correcao.get_resposta_completa())


st.set_page_config(page_title=f"Writing Evaluator {PROVA.upper()} with Gemini", page_icon="📝", layout="wide")

st.markdown(
'''
<style>
    [data-testid="stSidebar"][aria-expanded="true"]{
        min-width: 30%;
        max-width: 900px;
    }
</style>
''',
unsafe_allow_html=True
)

default_tema = ""
default_textos_motivadores = ""
default_redacao_aluno = "" 

with st.sidebar:
    st.write(f"Writing Evaluator {PROVA.upper()} with Gemini")


    # Selcionando um dos exemplos
    st.write("### Examples")
    exemplos = [json.load(open(f'data/{file}', 'r', encoding='utf-8')) for file in os.listdir('data')]
    exemplo = st.selectbox("Choose an Example", [f"{exemplo['tema']}" for exemplo in exemplos])
    notasProfessores = None

    if st.button("Load sample"):
        ex = exemplos[[f"{exemplo['tema']}" for exemplo in exemplos].index(exemplo)]
        default_tema = ex['tema']
        default_textos_motivadores = ex['textosMotivadores']
        default_redacao_aluno = ex['texto']

        st.write(notasProfessores)
    
    tema_redacao = st.text_input("Essay Theme", default_tema)
    textos_motivadores = st.text_area("Support texts:", default_textos_motivadores, height=200)
    redacao_aluno = st.text_area("Student Essay", default_redacao_aluno, height=350)

    st.button("Submit", on_click=on_submit_redacao)