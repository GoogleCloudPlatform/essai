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

from streamlit import session_state as state

import streamlit as st
import pandas as pd
import numpy as np

def agregar_descricoes(row):
    descs = row['descricoes']
    notas = pd.Series(row['notas'])
    nota_enem = int(np.ceil(notas.sum()/(len(notas) * 2))*40)
    acc = f"#### Competência {row.name[-1]}   \n<strong>ENEM:</strong> {nota_enem}/200 &emsp; \n"
    for key in descs:
      acc += f"\n- **{key.replace('_', ' ').replace('desc', '').strip().capitalize()}**: "
      acc += f'{descs[key]}'
    return acc


def display_redacao(redacao, i, col):
    col.markdown('---')
    col.header(f"Redação {i+1}")
    col.write(f"**Tema:** {redacao['proposal_name']}")
    col.write(f"**Texto:** {redacao['text'][:75]}...")
    if col.button(f"Corrigir Redação {i+1}"):
        state.redacao = redacao
        state.page = 'correcoes'
        st.switch_page("st_pages/correcoes.py")

