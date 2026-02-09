import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import datetime

# --- 1. GERENCIAMENTO DE BANCO DE DADOS (O Cérebro) ---
def init_db():
    """Cria a tabela se ela não existir."""
    conn = sqlite3.connect('precificacao.db')
    c = conn.cursor()
    # Tabela simples para guardar o perfil do cliente
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            cnpj TEXT PRIMARY KEY,
            nome_empresa TEXT,
            regime_tributario TEXT,
            custo_fixo_padrao REAL,
            margem_alvo REAL
        )
    ''')
    conn.commit()
    conn.close()

def carregar_dados(cnpj):
    conn = sqlite3.connect('precificacao.db')
    df = pd.read_sql(f"SELECT * FROM clientes WHERE cnpj = '{cnpj}'", conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

def salvar_dados(cnpj, nome, regime, custo_fixo, margem_alvo):
    conn = sqlite3.connect('precificacao.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO clientes (cnpj, nome_empresa, regime_tributario, custo_fixo_padrao, margem_alvo)
        VALUES (?, ?, ?, ?, ?)
    ''', (cnpj, nome, regime, custo_fixo, margem_alvo))
    conn.commit()
    conn.close()
    st.success(f"Dados da empresa {nome} salvos com sucesso!")

# --- 2. APLICAÇÃO PRINCIPAL ---
def app():
    st.title("💎 Precificação Estratégica & Fiscal")
    st.markdown("---")
    
    # Inicializa o banco
    init_db()

    # --- SIDEBAR: Identificação do Cliente ---
    st.sidebar.header("📂 Identificação")
    cnpj_input = st.sidebar.text_input("CNPJ do Cliente (apenas números)")
    
    dados_cliente = None
    if cnpj_input:
        dados_cliente = carregar_dados(cnpj_input)
        if dados_cliente is not None:
            st.sidebar.success(f"Cliente: {dados_cliente['nome_empresa']}")
            st.sidebar.info(f"Regime: {dados_cliente['regime_tributario']}")
        else:
            st.sidebar.warning("Novo Cliente detectado.")

    # Se não tiver CNPJ, pede para preencher
    if not cnpj_input:
        st.warning("👈 Por favor, digite um CNPJ na barra lateral para começar.")
        return

    # --- INPUTS GERAIS (Carrega do banco se existir) ---
    with st.expander("⚙️ Configurações Globais do Cliente (Salvar no Banco)", expanded=(dados_cliente is None)):
        c1, c2, c3 = st.columns(3)
        nome_empresa = c1.text_input("Nome da Empresa", value=dados_cliente['nome_empresa'] if dados_cliente is not None else "")
        regime = c2.selectbox("Regime Tributário", ["Simples Nacional", "Lucro Presumido", "Lucro Real"], 
                              index=["Simples Nacional", "Lucro Presumido", "Lucro Real"].index(dados_cliente['regime_tributario']) if dados_cliente is not None else 0)
        
        # Botão de salvar configurações
        if st.button("💾 Salvar Perfil do Cliente"):
            salvar_dados(cnpj_input, nome_empresa, regime, 0, 0) # Simplificado para exemplo
            st.rerun()

    # --- NAVEGAÇÃO ENTRE MÓDULOS ---
    tab1, tab2, tab3 = st.tabs(["1️⃣ Calculadora de Preço (Markup)", "2️⃣ Análise Reversa (Margem)", "3️⃣ Diagnóstico Estratégico"])

    # === TAB 1: MARKUP (Caminho de Ida) ===
    with tab1:
        st.subheader("Quanto devo cobrar?")
        col_custo, col_taxas = st.columns(2)
        
        with col_custo:
            custo_prod = st.number_input("Custo do Produto/Serviço (R$)", min_value=0.0, value=100.0)
        
        with col_taxas:
            imposto_pct = st.number_input("Impostos (%)", value=10.0 if regime == "Simples Nacional" else 18.0)
            fixas_pct = st.number_input("Despesas Fixas (%)", value=15.0)
            lucro_alvo_pct = st.number_input("Margem de Lucro Desejada (%)", value=20.0)
        
        total_deducoes = imposto_pct + fixas_pct + lucro_alvo_pct
        
        if total_deducoes < 100:
            divisor = (100 - total_deducoes) / 100
            preco_sugerido = custo_prod / divisor
            st.metric("Preço de Venda Sugerido", f"R$ {preco_sugerido:,.2f}")
        else:
            st.error("A soma das porcentagens ultrapassa 100%. Impossível calcular.")

    # === TAB 2: ANÁLISE REVERSA (Caminho de Volta) ===
    with tab2:
        st.subheader("O mercado paga X. Quanto me sobra?")
        
        col_rev1, col_rev2 = st.columns(2)
        preco_mercado = col_rev1.number_input("Preço Praticado no Mercado (R$)", value=200.0)
        custo_rev = col_rev2.number_input("Custo do Produto (R$)", value=custo_prod)
        
        # Cálculos Reversos
        v_imposto = preco_mercado * (imposto_pct/100)
        v_fixas = preco_mercado * (fixas_pct/100)
        
        lucro_real = preco_mercado - custo_rev - v_imposto - v_fixas
        margem_real_pct = (lucro_real / preco_mercado) * 100
        
        # Exibição
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("Lucro Real (R$)", f"R$ {lucro_real:,.2f}", delta_color="normal")
        c_m2.metric("Margem Real (%)", f"{margem_real_pct:.2f}%", 
                    delta=f"{margem_real_pct - lucro_alvo_pct:.2f}% vs Meta",
                    delta_color="normal" if margem_real_pct >= lucro_alvo_pct else "inverse")
        
        if margem_real_pct < 0:
            st.error("🚨 PREJUÍZO OPERACIONAL: Este preço não cobre os custos!")

    # === TAB 3: DIAGNÓSTICO ESTRATÉGICO (Suas Ideias Malucas) ===
    with tab3:
        st.subheader("🔍 Raio-X do Negócio")
        
        # 1. Sanidade Fiscal
        st.markdown("#### 1. Os Impostos foram considerados?")
        preco_minimo_fiscal = custo_prod / (1 - (imposto_pct/100))
        if preco_mercado < preco_minimo_fiscal:
            st.warning(f"⚠️ **PERIGO:** O preço de R$ {preco_mercado} não cobre nem o Custo + Impostos (R$ {preco_minimo_fiscal:.2f}). Você está pagando imposto sobre o prejuízo.")
        else:
            st.success("✅ **OK:** O preço cobre Custo + Impostos.")

        st.markdown("---")

        # 2. Preservação de Margem
        st.markdown("#### 2. A margem está preservada?")
        if margem_real_pct >= lucro_alvo_pct:
            st.success(f"Sim! Sua margem atual ({margem_real_pct:.1f}%) é superior à meta ({lucro_alvo_pct:.1f}%).")
        else:
            perda = lucro_alvo_pct - margem_real_pct
            st.error(f"Não. Você está queimando {perda:.1f}% de margem para competir no preço.")

        st.markdown("---")

        # 3. Financiamento do Crescimento
        st.markdown("#### 3. Origem do Crescimento")
        col_fin1, col_fin2 = st.columns(2)
        lucro_retido = col_fin1.number_input("Lucro Reinvestido no Período (R$)", value=50000.0)
        divida_nova = col_fin2.number_input("Novos Empréstimos/Dívidas (R$)", value=20000.0)
        
        total_investido = lucro_retido + divida_nova
        if total_investido > 0:
            pct_proprio = (lucro_retido / total_investido) * 100
            
            fig_fin = px.bar(
                x=[lucro_retido, divida_nova], 
                y=["Capital Próprio", "Endividamento"], 
                orientation='h',
                labels={'x': 'Valor (R$)', 'y': 'Fonte'},
                title="Estrutura de Financiamento do Crescimento",
                color=["Capital Próprio", "Endividamento"],
                color_discrete_map={"Capital Próprio": "green", "Endividamento": "red"}
            )
            st.plotly_chart(fig_fin, use_container_width=True)
            
            if divida_nova > lucro_retido:
                st.warning("⚠️ **Atenção:** Seu crescimento está alavancado (baseado em dívida). Risco financeiro elevado.")
            else:
                st.success("✅ **Saudável:** Crescimento sustentado majoritariamente por geração de caixa própria.")

if __name__ == "__main__":
    app()
