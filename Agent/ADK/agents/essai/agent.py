# Importações baseadas no exemplo da sua documentação
# LlmAgent (ou Agent) vem de google.adk.agents
from google.adk.agents import LlmAgent, Agent
# Em vez de 'Tool' e 'tool' diretamente, usaremos FunctionTool se Tool não for acessível
# A documentação que você colou mostra "from google.adk.tools import FunctionTool"
from google.adk.tools import FunctionTool, agent_tool, ToolContext
from essai.essay_corrector_agent import enem_corrector_agent

# Sumarizador para feedback no formato ENEM
sumarizador_enem = LlmAgent(
    name="sumarizador_enem",
    model="gemini-2.0-flash-001",
    instruction=(
        "Você é um corretor de redação do ENEM. Receba o resultado da correção no state['resultado_correcao'] "
        "com as notas das 5 competências (cada uma de 0 a 200, sempre múltiplos de 40), nota final (0 a 1000), correções e observações. "
        "Gere um feedback estruturado e motivador para o aluno, SEMPRE em texto corrido, nunca em formato JSON, tabela ou código. "
        "Explique os pontos fortes e o que pode ser melhorado em cada competência, e dê recomendações práticas e motivacionais para o aluno melhorar sua redação. "
        "Nunca omita as notas de cada competência nem a nota final."
        "\n\nExemplo de uso do state: Use as informações de state['resultado_correcao'] para montar o feedback."
    ),
    output_key="feedback_enem"
)

sumarizador_enem_agent_tool = agent_tool.AgentTool(agent=sumarizador_enem)

def gerar_feedback_enem(competencias, nota_final):
    bloco_notas = "\n".join(competencias) + f"\nNota Final: {nota_final}\n"
    prompt = (
        f"{bloco_notas}\n"
        "Com base nessas notas, escreva um feedback motivador, claro e personalizado para o aluno, explicando os pontos fortes e o que pode ser melhorado em cada competência. "
        "Não repita as notas, apenas explique e motive o aluno. Não use JSON, tabela ou código."
    )
    return sumarizador_enem.invoke(prompt)

def corrigir_redacao_tool(tema: str, textos_motivadores: str, redacao: str, tool_context: ToolContext) -> dict:
    """
    Corrige a redação do aluno usando o agente de correção externo.
    Salva o resultado no state para o sumarizador_enem acessar.
    """
    if not tema or not textos_motivadores or not redacao:
        return {"status": "error", "error_message": "Todos os campos (tema, textos motivadores e redação) são obrigatórios."}
    resultado = enem_corrector_agent.corrigir_redacao_api(tema, textos_motivadores, redacao)
    # Salva o resultado no state para o sumarizador_enem acessar
    tool_context.state["resultado_correcao"] = resultado
    return {"status": "success", "message": "Correção realizada com sucesso."}

# 2. Definição do seu Agente Raiz (root_agent)
# Em vez de CorretorTool(), passaremos a função diretamente
root_agent = LlmAgent(
    name="ProfessorEnemAgent",
    model="gemini-2.0-flash-001",
    instruction=(
        "Você é um professor de redação do ENEM, experiente, empático e motivador. "
        "Assim que receber o tema, os textos motivadores e a redação do aluno, use a ferramenta 'corrigir_redacao_tool' para corrigir. "
        "Depois, transfira imediatamente para o agente 'sumarizador_enem' para gerar o feedback final, sem enviar mensagens intermediárias ou de espera. "
        "Nunca diga que vai corrigir, que está processando ou que vai apresentar o resultado em instantes. "
        "Apenas envie o feedback final, estruturado e motivador, conforme o resultado da correção."
        "Nunca mencione ferramentas, processos internos ou termos técnicos de programação."
        "\n\nQuando a correção estiver pronta, use transfer_to_agent(agent_name='sumarizador_enem') para passar o controle ao agente de feedback."
    ),
    tools=[FunctionTool(func=corrigir_redacao_tool)],
    sub_agents=[sumarizador_enem]
)