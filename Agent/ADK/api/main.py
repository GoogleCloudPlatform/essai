from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import json
from corretor_gemini.gemini_corretor import Corretor, Correcao
import os

app = FastAPI(title="Corretor de Redação ENEM")

class RedacaoRequest(BaseModel):
    tema: str
    textos_motivadores: str
    redacao: str

@app.post("/corrigir-redacao/", response_model=Dict[str, Any])
async def corrigir_redacao(request: RedacaoRequest):
    try:
        # Configuração do corretor
        corretor = Corretor(
            caminho_prompts="Prompts",
            corretor_path="Enem",
            project="key-range-436019-t9",
            dummy=False,
            ignore_json=False
        )
        # Preparar dados para correção
        redacao_data = {
            "tema": request.tema,
            "textos_motivadores": request.textos_motivadores,
            "redacao_estudante": request.redacao,
            "enunciado": ""
        }
        
        # Executar correção
        correcao = corretor.get_correcao_from_redacao(redacao_data)
        
        # Processar resposta
        resposta = construir_resposta(correcao)
        return resposta
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422, 
            detail=f"Erro ao decodificar resposta do modelo: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro na correção da redação: {str(e)}"
        )

def construir_resposta(correcao: Correcao) -> Dict[str, Any]:
    # Estrutura base da resposta
    response = {
        "nota_final": 0,
        ##"sumarizacao": "",
        #"comentarios": correcao.get_comentarios(),
        "competencias": {},
        "detalhes": {}
    }
    
    # Processar competências se existirem dados estruturados
    if hasattr(correcao, 'correcao_data'):
        for i in range(1, 6):
            competencia_key = f"competencia_{i}"
            if competencia_key in correcao.correcao_data:
                competencia = correcao.correcao_data[competencia_key]
                
                # Detalhes das notas
                response["competencias"][competencia_key] = {
                    "nota_total": int((sum(competencia["notas"].values())/len(competencia["notas"].values())//2) * 40),  # Conversão para escala ENEM
                    "criterios": competencia["notas"]
                }
                
                # Detalhes das descrições
                response["detalhes"][competencia_key] = {}
                for criterio, descricao in competencia["descricoes"].items():
                    nome_criterio = criterio.replace('desc_', '').replace('_', ' ').title()
                    response["detalhes"][competencia_key][nome_criterio] = descricao
    
    response["nota_final"] = int(sum([response["competencias"][c]["nota_total"] for c in response["competencias"]]))
    return response

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)