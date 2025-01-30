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

"""
 Copyright 2024 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """

import json
import os
import streamlit as st
from typing import List, Dict


FILEPATH_ESSAYS_CATALOG = "data/"

# Carregar exemplos de redação apenas uma vez
ESSAYS_CATALOG = [
    json.load(open(os.path.join(FILEPATH_ESSAYS_CATALOG, fp), 'r', encoding='utf-8'))
    for fp in os.listdir(FILEPATH_ESSAYS_CATALOG)
]

def load_catalog(path: str) -> List[Dict]:
    """
    Loads the catalog of essays from the specified directory.

    Args:
        path (str): The directory path containing essay data.

    Returns:
        List[Dict]: A list of essays loaded from JSON files.
    """
    catalog = []
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            catalog.append(json.load(file))
    return catalog

def load_essay_from_catalog(index: int, catalog: List[Dict] = ESSAYS_CATALOG) -> None:
    """
    Loads an essay from the catalog into the session state.

    Args:
        catalog (List[Dict]): The catalog of essays.
        index (int): The index of the essay to load.
    """
    try:
        essay = catalog[index]
        st.session_state["tema"] = essay.get('tema', '')
        st.session_state["textos_motivadores"] = essay.get('textosMotivadores', '')
        st.session_state["redacao_aluno"] = essay.get('texto', '').replace("\n", "\n\n")
        st.session_state["proposta"] = essay.get('textoProposta', '')
    except IndexError:
        st.error("Exemplo inválido.")