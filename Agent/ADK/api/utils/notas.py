import pandas as pd
import numpy as np

def calcular_nota_competencia(row):
    notas = pd.Series(row['notas'])
    return int(np.ceil(notas.sum()/(len(notas) * 2))*40)
    