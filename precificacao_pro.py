import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="Gestor de Precificação", layout="wide")

def init_db():
    conn = sqlite3.connect('precificacao_pro.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historico_simulacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            data_simulacao TIMESTAMP,
            tipo_calculo TEXT,
            custo_produto REAL,
            preco_venda REAL,
            margem_pct REAL,
            lucro_liquido REAL,
            detalhes_impostos TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_simulacao(cnpj, tipo, custo, preco, margem, lucro, info_impostos):
    conn = sqlite3.connect('precificacao_pro.db')
    c = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO historico_simulacoes (cnpj, data_simulacao, tipo_calculo, custo_produto, preco_venda, margem_pct, lucro_liquido, detalhes_impostos)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (cnpj, data_hora, tipo, custo, preco, margem, lucro, info_impostos))
    conn.commit()
    conn.close()
    st.toast("✅ Simulação salva com sucesso!", icon="💾")

def carregar_historico(cnpj):
    conn = sqlite3.connect('precificacao_pro.db')
    df = pd.read_sql(f"SELECT * FROM historico_simulacoes WHERE cnpj = '{cnpj}' ORDER BY data_simulacao DESC", conn)
    conn.close()
    return df

# --- 2. APLICAÇÃO PRINCIPAL ---
def app():
    st.title("💎 Precificação Profissional")
    st.markdown("---")
    init_db()

    # --- SIDEBAR: IDENTIFICAÇÃO ---
    with st.sidebar:
        st.header("📂 Cliente")
        cnpj_input = st.text_input("CNPJ", placeholder="Digite apenas números")
        
        if not cnpj_input:
            st.warning("Digite o CNPJ para começar.")
            return

        st.info(f"Trabalhando no CNPJ: {cnpj_input}")
        st.markdown("---")
        
        # --- INPUT FUNDAMENTAL: FATURAMENTO ---
        st.header("💰 Base de Cálculo")
        st.caption("Necessário para calcular o % das despesas fixas.")
        faturamento_medio = st.number_input(
            "Faturamento Médio Mensal (R$)", 
            min_value=1.0, 
            value=50000.0, 
            step=1000.0,
            help="Quanto a empresa vende em média por mês? Usado para ratear aluguel, luz, etc."
        )

    # --- ETAPA 1: DEFINIÇÃO DE CUSTOS E DESPESAS (PREPARAÇÃO) ---
    st.subheader("1. Estrutura de Custos e Impostos")
    
    col_impostos, col_fixas = st.columns(2)

    # --- BLOCO DE IMPOSTOS DETALHADOS ---
    with col_impostos:
        st.markdown("### 🏛️ Tributação")
        tipo_atividade = st.radio("Atividade Principal", ["Serviço (ISS)", "Comércio/Revenda (ICMS)"], horizontal=True)
        
        with st.expander("Detalhamento de Alíquotas", expanded=True):
            c_pis, c_cofins = st.columns(2)
            pis = c_pis.number_input("PIS (%)", value=0.65, step=0.01)
            cofins = c_cofins.number_input("COFINS (%)", value=3.00, step=0.01)
            
            ir_csll = st.number_input("IRPJ + CSLL (%) (Se houver)", value=2.0, step=0.1)
            
            if "Serviço" in tipo_atividade:
                iss_icms = st.number_input("ISSQN (%)", value=5.0, step=0.1)
                texto_imposto_especifico = "ISS"
            else:
                iss_icms = st.number_input("ICMS Médio (%)", value=18.0, step=0.5)
                texto_imposto_especifico = "ICMS"
            
            # Soma total automática
            total_impostos_pct = pis + cofins + ir_csll + iss_icms
            st.info(f"**Carga Tributária Total: {total_impostos_pct:.2f}%**")

    # --- BLOCO DE DESPESAS FIXAS (LISTA EM REAIS) ---
    with col_fixas:
        st.markdown("### 🏢 Despesas Fixas")
        st.caption("Liste suas contas mensais (Aluguel, Luz, Contador, Software...)")
        
        # Data Editor permite adicionar linhas como no Excel
        df_template = pd.DataFrame([
            {"Descrição": "Aluguel", "Valor (R$)": 2000.00},
            {"Descrição": "Contador", "Valor (R$)": 600.00},
            {"Descrição": "Internet/Luz", "Valor (R$)": 400.00},
        ])
        
        df_despesas = st.data_editor(df_template, num_rows="dynamic", use_container_width=True)
        
        total_despesas_reais = df_despesas["Valor (R$)"].sum()
        
        # O PULO DO GATO: Converte R$ em % baseado no faturamento
        percentual_fixo = (total_despesas_reais / faturamento_medio) * 100
        
        st.metric(
            label="Total Despesas Fixas", 
            value=f"R$ {total_despesas_reais:,.2f}", 
            delta=f"Representa {percentual_fixo:.2f}% do Faturamento"
        )

    st.markdown("---")

    # --- ETAPA 2: CÁLCULO DO PREÇO ---
    st.subheader("2. Formação do Preço")
    
    tab_markup, tab_margem = st.tabs(["Calculadora de Preço (Markup)", "Análise de Margem Real"])

    # === ABA MARKUP ===
    with tab_markup:
        c1, c2, c3 = st.columns(3)
        custo_direto = c1.number_input("Custo Direto do Produto/Serviço (R$)", value=100.0, step=1.0)
        comissao_pct = c2.number_input("Comissões/Taxas de Cartão (%)", value=5.0)
        margem_desejada = c3.number_input("Margem de Lucro Líquida (%)", value=20.0)

        # Cálculo
        total_deducoes = total_impostos_pct + percentual_fixo + comissao_pct + margem_desejada
        
        if total_deducoes >= 100:
            st.error(f"🚨 A soma das porcentagens ({total_deducoes:.2f}%) inviabiliza o negócio. Aumente o preço ou reduza custos.")
        else:
            divisor = (100 - total_deducoes) / 100
            preco_sugerido = custo_direto / divisor
            lucro_valor = preco_sugerido * (margem_desejada / 100)

            # Exibição dos Resultados
            st.markdown("#### ✅ Resultado Sugerido")
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Preço de Venda Ideal", f"R$ {preco_sugerido:,.2f}")
            col_res2.metric("Lucro Líquido", f"R$ {lucro_valor:,.2f}")
            col_res3.metric("Markup Multiplicador", f"{preco_sugerido/custo_direto:.2f}x")

            # Gráfico de Rosca
            df_chart = pd.DataFrame({
                "Item": ["Custo Produto", "Impostos", "Despesas Fixas", "Comissões", "Lucro"],
                "Valor": [
                    custo_direto, 
                    preco_sugerido * (total_impostos_pct/100),
                    preco_sugerido * (percentual_fixo/100),
                    preco_sugerido * (comissao_pct/100),
                    lucro_valor
                ]
            })
            fig = px.pie(df_chart, values='Valor', names='Item', title='Para onde vai o dinheiro da venda?', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

            if st.button("💾 Salvar Preço no Histórico", key="save_markup"):
                info_imposto_str = f"Total: {total_impostos_pct}% ({texto_imposto_especifico})"
                salvar_simulacao(cnpj_input, "Markup", custo_direto, preco_sugerido, margem_desejada, lucro_valor, info_imposto_str)

    # === ABA ANÁLISE DE MARGEM ===
    with tab_markup: # Mantivemos na mesma estrutura visual, mas na lógica pode separar
       pass # O código da aba 2 seria similar, usando as variáveis calculadas acima.

    # Histórico Rápido
    with st.expander("Ver Histórico de Simulações"):
        df_hist = carregar_historico(cnpj_input)
        if not df_hist.empty:
            st.dataframe(df_hist)
        else:
            st.info("Nenhuma simulação salva ainda.")

if __name__ == "__main__":
    app()
