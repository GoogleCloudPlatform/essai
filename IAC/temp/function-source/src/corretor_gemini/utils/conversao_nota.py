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

notas_enem_para_estado  = {
    200 : 15,
    160 : 12,
    120 : 10,
    80 : 7,
    40 : 4,
    0 : 0
}

def nota_enem_para_estado(nota):
    '''
    Converte a nota do ENEM para a nota do estado do Paraná.
    
    Args:
        nota (int): Nota do ENEM.
    
    Returns:
        int: Nota do estado do Paraná.
    '''
    acc = 0
    while nota > 0:
        for key in notas_enem_para_estado:
            if nota >= key:
                acc += notas_enem_para_estado[key]
                nota -= key
                break
    return acc