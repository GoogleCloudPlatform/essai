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

