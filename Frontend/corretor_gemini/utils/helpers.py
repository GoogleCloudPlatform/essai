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

import pandas as pd
import numpy as np

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