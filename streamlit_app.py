import streamlit as st
import pandas as pd

# ===============================
# 1. Regras de classificação (JCR + SJR)
# ===============================

def map_quartil_to_level(q):
    """
    Converte Q1/Q2/Q3/Q4 em MB/B/R/F.
    Retorna None se não for quartil válido.
    """
    if q is None:
        return None
    s = str(q).strip().upper()
    if s == "Q1":
        return "MB"
    if s == "Q2":
        return "B"
    if s == "Q3":
        return "R"
    if s == "Q4":
        return "F"
    return None

def classify_journal(jcr_quartil, sjr_quartil):
    """
    - Se JCR = Q1 ou SJR = Q1 -> MB
    - Senão, se JCR = Q2 ou SJR = Q2 -> B
    - Senão, se JCR = Q3 ou SJR = Q3 -> R
    - Senão, se JCR = Q4 ou SJR = Q4 -> F
    - Sem quartil válido -> SEM_CLASSIFICACAO_JCR_SJR
    """
    jcr_level = map_quartil_to_level(jcr_quartil)
    sjr_level = map_quartil_to_level(sjr_quartil)

    ordem = ["MB", "B", "R", "F"]
    for lvl in ordem:
        if jcr_level == lvl or sjr_level == lvl:
            return lvl

    return "SEM_CLASSIFICACAO_JCR_SJR"


@st.cache_data
def load_data():
    """
    Lê a base JCR_SCImago_integrado_classificado.xlsx
    (que deve estar na mesma pasta do app no Streamlit Cloud/GitHub)
    e garante a coluna 'Classificação'.
    """
    df = pd.read_excel("JCR_SCImago_integrado_classificado.xlsx")

    # Se, por algum motivo, a coluna 'Classificação' não existir,
    # recalcula com base em Quartil_JCR e SJR_Quartil.
    if "Classificação" not in df.columns:
        df["Classificação"] = df.apply(
            lambda row: classify_journal(
                row.get("Quartil_JCR"),
                row.get("SJR_Quartil")
            ),
            axis=1
        )

    return df


# ===============================
# 2. Layout e interatividade
# ===============================

st.set_page_config(
    page_title="Classificador de Periódicos PPGSUECE",
    layout="wide"
)

st.title("Classificador de Periódicos PPGSUECE")

st.markdown(
    """
#### Classificador de Periódicos – JCR & SJR  

Aplicação para consulta e classificação de periódicos com base nos quartis do **JCR** e do **SCImago (SJR)**.  
Os rótulos são: **MB, B, R, F** e **SEM_CLASSIFICACAO_JCR_SJR** (quando não há JCR nem SJR disponíveis).
"""
)


df = load_data()

# -------------------------------
# 2.1. Sidebar – filtros globais
# -------------------------------
st.sidebar.header("Filtros")

# Classes disponíveis (na ordem desejada)
classes_order = ["MB", "B", "R", "F", "SEM_CLASSIFICACAO_JCR_SJR"]
classes_avail = [c for c in classes_order if c in df["Classificação"].unique()]

classe_sel = st.sidebar.multiselect(
    "Classificação",
    options=classes_avail,
    default=classes_avail,
)

# Quartis JCR e SJR
jcr_opts = sorted(df["Quartil_JCR"].dropna().astype(str).unique())
sjr_opts = sorted(df["SJR_Quartil"].dropna().astype(str).unique())

jcr_sel = st.sidebar.multiselect(
    "Quartil JCR",
    options=jcr_opts,
    default=jcr_opts
)

sjr_sel = st.sidebar.multiselect(
    "Quartil SJR",
    options=sjr_opts,
    default=sjr_opts
)

# Áreas (SCI) – se existir
area_col = "Áreas_SCI" if "Áreas_SCI" in df.columns else None
if area_col:
    areas_opts = sorted(df[area_col].dropna().unique())
    areas_sel = st.sidebar.multiselect(
        "Área / Campo (SCImago)",
        options=areas_opts,
        default=areas_opts
    )
else:
    areas_sel = None

# -------------------------------
# 2.2. Aplicar filtros
# -------------------------------
df_filt = df.copy()

if classe_sel:
    df_filt = df_filt[df_filt["Classificação"].isin(classe_sel)]

if jcr_sel:
    df_filt = df_filt[df_filt["Quartil_JCR"].astype(str).isin(jcr_sel)]

if sjr_sel:
    df_filt = df_filt[df_filt["SJR_Quartil"].astype(str).isin(sjr_sel)]

if area_col and areas_sel:
    df_filt = df_filt[df_filt[area_col].isin(areas_sel)]

# -------------------------------
# 2.3. Busca por título ou ISSN
# -------------------------------
st.subheader("Consulta de Periódicos")

col1, col2 = st.columns([2, 1])

with col1:
    termo = st.text_input(
        "Buscar por título ou ISSN",
        value="",
        placeholder="Ex.: 'Public Health' ou '1234-5678'"
    )

if termo:
    termo_norm = termo.strip().lower()
    mask = (
        df_filt.get("Titulo_SCImago", "").astype(str).str.lower().str.contains(termo_norm)
        | df_filt.get("Titulo_JCR", "").astype(str).str.lower().str.contains(termo_norm)
        | df_filt.get("ISSN_SCImago", "").astype(str).str.contains(termo_norm)
    )
    df_view = df_filt[mask]
else:
    df_view = df_filt

st.write(f"{len(df_view)} periódicos encontrados com os filtros atuais.")

# Colunas a exibir na tabela
cols_to_show = []
for c in [
    "Titulo_SCImago", "Titulo_JCR", "ISSN_SCImago",
    "Classificação",
    "Quartil_JCR", "SJR_Quartil",
    "País", "Região",
    "Áreas_SCI", "Categorias_SCI", "Categorias_JCR"
]:
    if c in df_view.columns and c not in cols_to_show:
        cols_to_show.append(c)

st.dataframe(df_view[cols_to_show].reset_index(drop=True))

# -------------------------------
# 2.4. Dashboard simples
# -------------------------------
st.subheader("Resumo dos Periódicos Filtrados")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Distribuição por Classificação (MB/B/R/F/SEM)**")
    class_counts = df_filt["Classificação"].value_counts().reindex(classes_order, fill_value=0)
    st.bar_chart(class_counts)

with col_b:
    st.markdown("**Distribuição por Quartil JCR**")
    jcr_counts = df_filt["Quartil_JCR"].fillna("Sem JCR").value_counts().sort_index()
    st.bar_chart(jcr_counts)

# -------------------------------
# 2.5. Classificador manual (JCR + SJR)
# -------------------------------
st.subheader("Classificador Manual (JCR + SJR)")

c1, c2, c3 = st.columns(3)

with c1:
    jcr_manual = st.selectbox(
        "Quartil JCR",
        options=["", "Q1", "Q2", "Q3", "Q4"],
        index=0
    )

with c2:
    sjr_manual = st.selectbox(
        "Quartil SJR",
        options=["", "Q1", "Q2", "Q3", "Q4", "-"],
        index=0
    )

with c3:
    if st.button("Classificar"):
        jcr_val = jcr_manual if jcr_manual != "" else None
        sjr_val = sjr_manual if sjr_manual not in ["", "-"] else None
        classe = classify_journal(jcr_val, sjr_val)
        st.markdown(f"### Classe atribuída: **{classe}**")
