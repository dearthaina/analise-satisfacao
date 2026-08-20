import pandas as pd

def limpar_formulario(df):
    df = df.copy()

    # O formulário já possui a nota como numérica; é garantido o tipo e
    # transformado valores inválidos em nulos.
    df["nota_satisfacao"] = pd.to_numeric(df["nota_satisfacao"], errors="coerce")

    # Escala de satisfação vai de 0 a 10.
    df["nota_satisfacao"] = df["nota_satisfacao"].clip(lower=0, upper=10)

    # ID vem com prefixo "C" (ex: "C00103"). Removido o prefixo e convertido
    # para Int64, mesmo tipo usado nas outras duas bases, para o merge funcionar.
    ids = df["id_cliente"].astype(str).str.replace("^C", "", regex=True)
    df["id_cliente"] = pd.to_numeric(ids, errors="coerce").astype("Int64")

    df["produto"] = df["produto"].astype(str).str.strip()

    df["data_resposta"] = pd.to_datetime(
        df["data_resposta"], format="mixed", dayfirst=True, errors="coerce"
    )

    df = df.drop_duplicates()

    print("FORMULÁRIO DIGITAL")
    print("Nulos restantes:")
    print(df.isnull().sum())
    print("Duplicatas restantes:", df.duplicated().sum())

    return df

def limpar_atendimento(df):
    df = df.copy()

    # Converte notas por extenso ("dez") para número.
    mapa_notas = {
        "zero": 0, "um": 1, "dois": 2, "três": 3, "tres": 3,
        "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
        "oito": 8, "nove": 9, "dez": 10
    }
    notas = df["nota"].astype(str).str.strip().str.lower()
    notas = notas.replace(mapa_notas)
    df["nota"] = pd.to_numeric(notas, errors="coerce")

    # Nota fora da escala 0-10 (ex: "11") é tratada como erro de digitação
    # e truncada para o teto/piso da escala.
    df["nota"] = df["nota"].clip(lower=0, upper=10)

    # Datas em múltiplos formatos; dayfirst=True resolve os casos ambíguos
    # (dia e mês ambos ≤12) como DD/MM, consistente com o padrão brasileiro.
    df["data"] = pd.to_datetime(
        df["data"], format="mixed", dayfirst=True, errors="coerce"
    )

    df["codigo_cliente"] = pd.to_numeric(df["codigo_cliente"], errors="coerce").astype("Int64")

    # De-para manual: produto tem poucas categorias reais e algumas variações
    # são abreviação (ex: "Carteira Adm"), não só diferença de formatação.
    mapa_produtos = {
        "c.d.b.": "CDB",
        "cdb": "CDB",
        "carteira administrada": "Carteira Administrada",
        "carteira adm": "Carteira Administrada",
        "fundos de investimento": "Fundos",
        "fundo": "Fundos",
        "fundos": "Fundos",
        "tesouro": "Tesouro Direto", 
        "tesouro direto": "Tesouro Direto",
        "c.o.e.": "COE",
        "coe": "COE",
    }
    produtos = df["produto_investimento"].astype(str).str.strip().str.lower()
    df["produto_investimento"] = produtos.replace(mapa_produtos)

    # Duplicata removida só depois de ID e data padronizados.
    df = df.drop_duplicates()

    print("ATENDIMENTO MANUAL")
    print("Nulos restantes:")
    print(df.isnull().sum())
    print("Duplicatas restantes:", df.duplicated().sum())

    return df


def limpar_extrato(df):
    df = df.copy()

    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")

    # Ausência de reclamação registrada é tratada como zero reclamações no período.
    df["qtd_reclamacoes_90d"] = pd.to_numeric(df["qtd_reclamacoes_90d"], errors="coerce").fillna(0)

    df["tempo_resolucao_horas"] = pd.to_numeric(df["tempo_resolucao_horas"], errors="coerce")
    df["qtd_acessos_app_30d"] = pd.to_numeric(df["qtd_acessos_app_30d"], errors="coerce")

    # Algumas linhas trazem fuso horário embutido (-03:00) e outras não.
    # Foi normalizado tudo para hora local (mesmo fuso, Brasília) para evitar
    # erro de mistura de tipos na conversão.
    df["survey_datetime"] = pd.to_datetime(
        df["survey_datetime"], format="mixed", dayfirst=True, errors="coerce", utc=True
    ).dt.tz_localize(None)

    df["trimestre"] = df["survey_datetime"].dt.to_period("Q")

    # produto_codigo não está no dicionário oficial; significado inferido pelo
    # padrão PRD_XXX. Padronizado para o mesmo nome canônico das outras bases.
    mapa_codigo_produto = {
        "PRD_CDB": "CDB",
        "PRD_FND": "Fundos",
        "PRD_TES": "Tesouro Direto",
        "PRD_CAR": "Carteira Administrada",
        "PRD_COE": "COE",
    }
    df["produto_codigo"] = df["produto_codigo"].map(mapa_codigo_produto)

    df = df.drop_duplicates()

    print("EXTRATO DO SISTEMA")
    print("Nulos restantes:")
    print(df.isnull().sum())
    print("Duplicatas restantes:", df.duplicated().sum())

    return df

def unificar_base(formulario, atendimento, extrato):
    formulario = formulario.copy()
    atendimento = atendimento.copy()
    extrato = extrato.copy()

    # data_resposta é inconsistente com o trimestre real (datas de um mesmo
    # trimestre_ref aparecem espalhadas o ano inteiro). Foi usado trimestre_ref,
    # que já vem correto no arquivo, convertendo "2025T3" para Period "2025Q3".
    formulario["trimestre"] = formulario["trimestre_ref"].str.replace("T", "Q")
    formulario["trimestre"] = pd.PeriodIndex(formulario["trimestre"], freq="Q")

    atendimento["trimestre"] = atendimento["data"].dt.to_period("Q")

    # Agrega atendimento para 1 linha por cliente e trimestre.
    atendimento_agregado = (
        atendimento
        .groupby(["codigo_cliente", "trimestre"], as_index=False)
        .agg(
            nota_media_atendimento=("nota", "mean"),
            qtd_atendimentos=("nota", "count")
        )
        .rename(columns={"codigo_cliente": "id_cliente"})
    )

    # Reclamações e acessos são somados (quantidades acumuláveis); tempo de
    # resolução é média (duração). suitability_pendente é flag (0/1): usado
    # "max" para marcar o cliente como pendente se houve pendência em
    # qualquer registro do trimestre.
    extrato_agregado = (
        extrato
        .groupby(["customer_id", "trimestre"], as_index=False)
        .agg(
            reclamacoes_90d=("qtd_reclamacoes_90d", "sum"),
            tempo_medio_resolucao=("tempo_resolucao_horas", "mean"),
            acessos_app_30d=("qtd_acessos_app_30d", "sum"),
            suitability_pendente=("suitability_pendente", "max")
        )
        .rename(columns={"customer_id": "id_cliente"})
    )

    # Formulário é a base principal (única com a nota declarada pelo cliente),
    # por isso left join: todo cliente/trimestre do formulário é preservado.
    base_unificada = formulario.merge(
        atendimento_agregado, on=["id_cliente", "trimestre"], how="left"
    )
    base_unificada = base_unificada.merge(
        extrato_agregado, on=["id_cliente", "trimestre"], how="left"
    )

    # Nulos em colunas de contagem/flag = ausência de registro no período,
    # tratados como zero. Nulos em colunas de média são mantidos, pois
    # representam ausência de base de cálculo, não um valor real igual a zero.
    colunas_contagem = ["qtd_atendimentos", "reclamacoes_90d", "acessos_app_30d", "suitability_pendente"]
    base_unificada[colunas_contagem] = base_unificada[colunas_contagem].fillna(0)

    print("BASE UNIFICADA")
    print("Quantidade de registros:", len(base_unificada))
    print("Nulos por coluna:")
    print(base_unificada.isnull().sum())
    print("Duplicatas restantes:", base_unificada.duplicated().sum())

    return base_unificada

if __name__ == "__main__":
    formulario = pd.read_csv("data/formulario_digital.csv")
    atendimento = pd.read_excel("data/atendimento_manual.xlsx")
    extrato = pd.read_csv("data/extrato_sistema.csv")

    formulario_limpo = limpar_formulario(formulario)
    atendimento_limpo = limpar_atendimento(atendimento)
    extrato_limpo = limpar_extrato(extrato)

    base_final = unificar_base(formulario_limpo, atendimento_limpo, extrato_limpo)

    base_final.to_csv("base_satisfacao_limpa.csv", index=False)