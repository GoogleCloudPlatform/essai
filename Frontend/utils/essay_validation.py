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

from typing import Optional
from promptweaver.core.prompt_template import PromptConfig
from promptweaver.clients.gemini.gemini_client import GeminiClient


def validate_essay(
    tema_redacao: str,
    enunciado_redacao: str,
    textos_motivadores: str,
    redacao_estudante: str,
    gemini_client: GeminiClient,
    prompt_template_path: str = "Prompts/template-validacao-enem.yml.j2",
    verbose: bool = False
) -> Optional[str]:
    """
    Evaluates the validity of an essay using Gemini.

    Args:
        tema_redacao (str): The theme of the essay.
        enunciado_redacao (str): The essay prompt or statement.
        textos_motivadores (str): The motivational texts.
        redacao_estudante (str): The student's essay text.
        gemini_client (GeminiClient): The Gemini client from PromptWeaver module.
        prompt_template_path (str, optional): Path to the prompt template file.
            Defaults to "Prompts/template-validacao-enem.yml.j2".
        verbose (bool, optional): If True, prints verbose output. Defaults to False.

    Returns:
        Optional[str]: The result of the validation ("Válida" or a message indicating invalidity),
            or None if an error occurs.

    Notes:
        The validation output is an optional enum, with one of the following values:
            - "Válida"
            - "Inválida - Texto Ilegível ou Ininteligível"
            - "Inválida - Desvio do Gênero Dissertativo-Argumentativo"
            - "Inválida - Cópia dos textos motivadores"
            - "Inválida - Violação aos Direitos Humanos"
    """
    # Prepare the event data
    evento_redacao = {
        "tema_redacao": tema_redacao,
        "enunciado_redacao": enunciado_redacao,
        "textos_motivadores": textos_motivadores,
        "redacao_estudante": redacao_estudante
    }

    # Load the prompt configuration
    try:
        validacao_prompt = PromptConfig.from_file(
            prompt_template_path, evento_redacao, verbose=verbose
        )
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        return None

    # Generate the content using Gemini
    try:
        response = gemini_client.generate_content(validacao_prompt)
        if verbose:
                print(f"Response from the Gemini model: {response}")
        if hasattr(response, 'text'):
            return response.text
        else:
            print("Invalid response from the Gemini model.")
            return None
    except Exception as e:
        print(f"Error connecting to the Gemini model: {e}")
        return None