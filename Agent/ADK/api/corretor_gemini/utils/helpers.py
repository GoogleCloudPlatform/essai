import pandas as pd
import numpy as np

def ajustar_nota(nota: float, valor_max_init: float = 10, valor_max_final: float = 10) -> float:
    return nota * (valor_max_final/valor_max_init)

def calcular_nota_competencia(row):
    '''
    Calcula a nota de cada competência da redação.

    Args:
        row (pd.Series): Linha de um DataFrame com as notas das competências.
    
    Returns:
        int: Nota da competência.
    '''
    notas = pd.Series(row['notas'])
    return int(np.ceil(notas.sum()/(len(notas) * 2))*40)

def agregar_descricoes(row):
    '''
    Agrega as descrições das competências de uma redação.
    
    Args:
        row (pd.Series): Linha de um DataFrame com as notas e descrições das competências.
    
    Returns:
        str: Descrição das competências da redação.
    '''
    descs = row['descricoes']
    notas = pd.Series(row['notas'])
    nota_enem = int(np.ceil(notas.sum()/(len(notas) * 2))*40)
    acc = f"#### Competência {row.name[-1]}   \n<strong>ENEM:</strong> {nota_enem}/200 &emsp; \n"
    for key in descs:
      acc += f"\n- **{key.replace('_', ' ').replace('desc', '').strip().capitalize()}**: "
      acc += f'{descs[key]}'
    return acc