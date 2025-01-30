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

from var_environment import var
import streamlit as st
import pandas as pd
import os

project=var.get('project_id')
location=var.get('location')

if __name__ == "__main__":
    realizar_correcao_page = st.Page(page="st_pages/corrigir.py", 
                                    icon="📝", 
                                    url_path='/realizar_correcao', 
                                    title='Realizar Correção')

    pg = st.navigation([
        realizar_correcao_page
    ], position='hidden')

    pg.run()