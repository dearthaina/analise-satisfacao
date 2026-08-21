# Análise de Satisfação de Clientes — Investimentos

Case técnico para vaga de estágio em Engenharia de Dados (Diretoria de Investimentos, Time de Experiência do Cliente). 

## Objetivo 

O objetivo é entender por que a satisfação dos clientes de investimentos caiu no último trimestre e produzir uma base de dados limpa e confiável para essa análise.

## Como rodar

```bash
pip install -r requirements.txt
python src/app.py
```

O script lê os arquivos brutos em `data/`, realiza a limpeza e unificação, e gera automaticamente:
- `output/base_satisfacao_limpa.csv` — base tratada e unificada
- `output/analise_satisfacao.xlsx` — relatório com tabelas e gráficos

Esses arquivos não são versionados no repositório (estão no `.gitignore`); são gerados a cada execução.

## Estrutura do repositório

```text
analise-satisfacao/
│
├── data/
│   ├── formulario_digital.csv
│   ├── atendimento_manual.xlsx
│   ├── extrato_sistema.csv
│   └── dicionario_dados_case.xlsx
│
├── src/
│   ├── app.py
│   └── gerar_relatorio.py
│
├── output/
│   └── # arquivos gerados durante a execução
│
├── .gitignore
├── requirements.txt
└── README.md
```

## Tecnologias utilizadas

- Python
- Pandas
- OpenPyXL
- Git/GitHub
- IA Generativa
- Excel

## Escolha das ferramentas

A solução foi desenvolvida em Python, utilizando principalmente a biblioteca pandas, considerando o volume de dados e a quantidade de arquivos disponíveis.

A utilização de SQL não foi considerada necessária neste cenário, pois o pandas atende às necessidades de leitura, limpeza, transformação e unificação das bases. A adoção de um banco de dados para esse volume de dados adicionaria complexidade à solução sem um benefício proporcional.

O uso de Python também facilita a implementação e o rastreamento das regras de tratamento aplicadas aos dados, como a conversão de notas por extenso (por exemplo, `"dez"` para `10`) e a padronização de diferentes formatos de identificadores e categorias.

Em um cenário com maior volume de dados, consultas recorrentes ou necessidade de acesso compartilhado por diferentes pessoas da equipe, a utilização de SQL e de um banco de dados poderia ser mais adequada.

## Decisões de limpeza

| Problema encontrado | Decisão tomada |
|---|---|
| ID do cliente em formatos diferentes por arquivo (`C00103`, `424`, `114`) | Padronizado para inteiro, removendo prefixo "C" e zeros à esquerda. Validado que os IDs coincidem entre os 3 arquivos após a conversão. |
| Nota por extenso no atendimento (ex: "dez") | Convertida para valor numérico via dicionário de conversão. |
| Nota fora da escala 0–10 (ex: "11") | Truncada para o teto da escala (10), assumindo erro de digitação. |
| Datas em múltiplos formatos, alguns ambíguos | Interpretação com `dayfirst=True`, assumindo padrão brasileiro (DD/MM) nos casos ambíguos, consistente com os demais formatos claros da mesma coluna. |
| `survey_datetime` (extrato) com fuso horário embutido em parte das linhas | Normalizado para hora local (Brasília), removendo a informação de fuso para evitar mistura de tipos. |
| Produto com 15 grafias diferentes para 5 produtos reais | Padronizado via dicionário de-para manual, já que parte das variações são abreviações (ex: "Carteira Adm"), não apenas diferença de formatação. |
| `data_resposta` (formulário) inconsistente com o trimestre declarado (datas de um mesmo `trimestre_ref` espalhadas ao longo do ano) | Usado o campo `trimestre_ref`, já correto no arquivo original, em vez de recalcular o trimestre a partir da data. |
| Duplicatas | Removidas somente após padronização de ID e data, para não deixar passar registros iguais escritos de forma diferente. |
| Nulos após a unificação em colunas de contagem (`qtd_atendimentos`, `reclamacoes_90d`, `acessos_app_30d`) | Tratados como zero — ausência de registro no período indica ausência do evento. |
| Nulos em colunas de média (`nota_media_atendimento`, `tempo_medio_resolucao`) | Mantidos como nulo — não existe "média zero" quando não há base de cálculo. |
| `suitability_pendente` (flag binária) na agregação por cliente/trimestre | Agregado com `max`: se houve pendência em qualquer registro do trimestre, o cliente é marcado como pendente naquele período. Soma ou média não fariam sentido para uma variável binária. |

## Limite de confiabilidade

As 3 fontes de dados têm níveis de detalhes diferentes e nem todo cliente aparece nas 3 simultaneamente: dos aproximadamente 467 clientes únicos identificados no formulário, cerca de 202 possuem registros correspondentes nas três fontes. Isso significa que qualquer cruzamento entre `nota_satisfacao` e variáveis operacionais (reclamações, tempo de resolução, atendimento) é representativo apenas desse subconjunto — não da base completa de respondentes.

## Relatório automatizado

`gerar_relatorio.py` gera um arquivo Excel (`output/analise_satisfacao.xlsx`) com tabelas e gráficos (evolução da nota por trimestre, e nota por produto ao longo do tempo), a partir da base limpa. A geração é automatizada e integrada ao fluxo principal (`app.py`), pensada para reprodutibilidade — caso a análise precise ser refeita com dados de trimestres futuros, o relatório visual é gerado sem trabalho manual adicional.
