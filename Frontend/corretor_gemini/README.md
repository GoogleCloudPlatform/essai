# Corretor Gemini

## Descrição
O `Corretor Gemini` é uma biblioteca para correção automática de redações utilizando o serviço Gemini. A biblioteca permite calcular notas de competências, notas totais e gerar comentários detalhados sobre a redação.

## Instalação
Para instalar a biblioteca, basta clonar o repositório

## Uso
Para utilizar a biblioteca, importe a classe `Corretor` e utilize seus métodos para corrigir uma redação. Veja o exemplo abaixo:

```python
from corretor_gemini.corretor import Corretor

# Dados da redação
redacao_data = {
    "tema_redacao": "Tema da Redação",
    "enunciado_redacao": "Enunciado da Redação",
    "textos_motivadores": "Textos Motivadores",
    "redacao_estudante": "Texto da Redação"
}

# Instancia o corretor
corretor = Corretor()

# Obtém a correção da redação
correcao = corretor.get_correcao_from_redacao(redacao_data)

# Exibe a nota total
print("Nota ENEM:", correcao.get_nota_enem())

# Exibe os comentários
print(correcao.get_comentarios())
```

## Possíveis Utilizações da Resposta da Correção

### Notas por Competência
A resposta da correção pode ser utilizada para gerar tabelas com as notas de cada competência. Veja o exemplo abaixo:

```python
# Obtém as notas por competência
notas_competencias = correcao.get_nota_comptencias()

# Exibe a tabela de notas
print(notas_competencias)
```

A tabela gerada será semelhante a esta:

| Competência 2 | Competência 3 | Competência 4 | Competência 5 |
|---------------|---------------|---------------|---------------|
| 160           | 140           | 180           | 200           |

### Comentários Detalhados
Os comentários detalhados podem ser agregados e exibidos em um formato legível:

```python
# Obtém os comentários
comentarios = correcao.get_comentarios()

# Exibe os comentários
print(comentarios)
```

Os comentários serão exibidos em um formato detalhado, explicando os pontos fortes e fracos da redação.
