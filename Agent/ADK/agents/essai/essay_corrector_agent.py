import os
from google.adk.agents import Agent
import requests

CORRECAO_API_URL = os.environ.get("CORRECAO_API_URL", "http://127.0.0.1:8000/corrigir-redacao/")

class EnemEssayAgent(Agent):
    def __init__(self):
        super().__init__(
            name="enem_essay_corrector_agent",
            model="gemini-2.0-flash-001",
            description=(
                "Agente especializado em corrigir redações do ENEM utilizando uma API externa."
            ),
            instruction=(
                "Você é um agente útil que corrige redações do ENEM. Utilize a ferramenta 'corrigir_redacao_api' para enviar o tema, textos motivadores e a redação para correção e retornar o resultado detalhado."
            ),
            tools=[self.corrigir_redacao_api],
        )

    def corrigir_redacao_api(self, tema: str, textos_motivadores: str, redacao: str) -> dict:
        """Envia uma redação para a API de correção e retorna o resultado.

        Args:
            tema (str): O tema da redação.
            textos_motivadores (str): Os textos motivadores.
            redacao (str): O texto da redação do aluno.

        Returns:
            dict: O resultado da correção da redação.
        """
        payload = {
            "tema": tema,
            "textos_motivadores": textos_motivadores,
            "redacao": redacao
        }
        try:
            response = requests.post(CORRECAO_API_URL, json=payload)
            response.raise_for_status() # Levanta um erro para códigos de status HTTP ruins
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error_message": f"Erro ao chamar a API de correção: {e}"}

# Instancia o agente especializado (não será o root_agent)
enem_corrector_agent = EnemEssayAgent() 