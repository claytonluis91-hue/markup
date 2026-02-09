import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestor de Precificação", layout="wide")

# --- FUNÇÕES DE BANCO DE DADOS (Mantendo a memória viva) ---
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

# --- APP PRINCIPAL ---
def app():
    st.title("💎 Sistema de Precificação Inteligente")
    init_db()

    # Identificação rápida no topo (Sidebar fica apenas para CNPJ)
    with st.sidebar:
        st.header("🏢 Identificação")
        cnpj_input = st.text_input("CNPJ do Cliente", placeholder="Apenas números")
        if not cnpj_input:
            st.warning("⚠️ Informe o CNPJ para começar.")
            return
        st.success(f"Cliente Ativo: {cnpj_input}")
        st.markdown("---")
        st.caption("Dica: Preencha as abas na ordem (1, 2, 3) para garantir que os cálculos usem os dados corretos.")

    # --- CRIAÇÃO DAS ABAS ---
    tab_config, tab_markup, tab_analise, tab_hist = st.tabs([
        "1️⃣ Configuração (Premissas)", 
        "2️⃣ Calculadora de Preço", 
        "3️⃣ Análise de Mercado",
        "4️⃣ Histórico"
    ])

    # ==============================================================================
    # ABA 1: CONFIGURAÇÃO (O CÉREBRO)
    # ==============================================================================
    with tab_config:
        st.subheader("⚙️ Definição de Parâmetros Globais")
        st.info("Preencha aqui os dados da empresa. Essas informações serão usadas automaticamente nas outras abas.")
        
        col_fat, col_imp = st.columns(2)
        
        # --- 1.1 Faturamento e Despesas Fixas ---
        with col_fat:
            st.markdown("#### 💰 Faturamento & Fixas")
            faturamento_medio = st.number_input(
                "Faturamento Médio Mensal (R$)", 
                min_value=1.0, value=50000.0, step=1000.0,
                help="Usado para calcular o peso das despesas fixas."
            )
            
            st.markdown("**Lista de Despesas Fixas (Mensal)**")
            df_template = pd.DataFrame([
                {"Descrição": "Aluguel", "Valor (R$)": 2500.00},
                {"Descrição": "Prolabore", "Valor (R$)": 5000.00},
                {"Descrição": "Contabilidade", "Valor (R$)": 800.00},
                {"Descrição": "Sistemas/Software", "Valor (R$)": 300.00},
            ])
            df_despesas = st.data_editor(df_template, num_rows="dynamic", use_container_width=True, key="editor_despesas")
            
            total_despesas_reais = df_despesas["Valor (R$)"].sum()
            percentual_fixo = (total_despesas_reais / faturamento_medio) * 100
            
            st.metric("Custo Fixo Total (R$)", f"R$ {total_despesas_reais:,.2f}")
            st.metric("Impacto no Preço (%)", f"{percentual_fixo:.2f}%", help="Esse é o % que será levado para o cálculo do preço.")

        # --- 1.2 Impostos ---
        with col_imp:
            st.markdown("#### 🏛️ Carga Tributária")
            regime = st.selectbox("Regime Tributário", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
            atividade = st.radio("Tipo de Atividade", ["Comércio (ICMS)", "Serviço (ISS)"], horizontal=True)
            
            # Campos de impostos
            c1, c2 = st.columns(2)
            pis_cofins = c1.number_input("PIS/COFINS (%)", value=3.65 if regime != "Simples Nacional" else 0.0)
            icms_iss = c2.number_input("ICMS/ISS (%)", value=18.0 if "Comércio" in atividade else 5.0)
            ir_csll = st.number_input("IRPJ/CSLL (%)", value=2.0 if regime != "Simples Nacional" else 0.0, help="Deixe 0 se for Simples (já incluso na alíquota única)")
            
            if regime == "Simples Nacional":
                st.caption("Nota: No Simples, some a alíquota total do anexo no campo ICMS/ISS ou divida conforme preferir.")
            
            total_impostos_pct = pis_cofins + icms_iss + ir_csll
            st.metric("Carga Tributária Total (%)", f"{total_impostos_pct:.2f}%", help="Esse % será descontado de cada venda.")

    # ==============================================================================
    # ABA 2: CALCULADORA (MARKUP) - PUXA DADOS DA ABA 1
    # ==============================================================================
    with tab_markup:
        st.subheader("🏷️ Formação de Preço de Venda")
        
        # Mostra o que está vindo da Aba 1
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <small>📡 <b>Dados carregados da Configuração:</b> Impostos: <b>{total_impostos_pct:.2f}%</b> | Despesas Fixas: <b>{percentual_fixo:.2f}%</b></small>
        </div>
        """, unsafe_allow_html=True)

        col_custo, col_margem = st.columns(2)
        
        with col_custo:
            custo_direto = st.number_input("Custo do Produto/Serviço (R$)", value=100.0, step=1.0)
            comissao_pct = st.number_input("Comissões / Taxas Cartão (%)", value=4.5)
        
        with col_margem:
            margem_desejada = st.number_input("Margem de Lucro Líquida Desejada (%)", value=20.0)
        
        # Cálculo Principal
        total_deducoes = total_impostos_pct + percentual_fixo + comissao_pct + margem_desejada
        
        st.markdown("---")
        
        if total_deducoes >= 100:
            st.error(f"🛑 <b>Cálculo Impossível!</b><br>A soma das deduções é {total_deducoes:.2f}%. Você precisa reduzir custos ou aceitar margem menor.", unsafe_allow_html=True)
        else:
            divisor = (100 - total_deducoes) / 100
            preco_venda = custo_direto / divisor
            lucro_venda = preco_venda * (margem_desejada / 100)
            markup_indice = preco_venda / custo_direto if custo_direto > 0 else 0

            # Exibição Visual
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Preço de Venda Sugerido", f"R$ {preco_venda:,.2f}")
            c_res2.metric("Lucro Líquido (Unitário)", f"R$ {lucro_venda:,.2f}")
            c_res3.metric("Markup Divisor", f"{markup_indice:.2f}")

            # Botão Salvar
            if st.button("💾 Salvar Preço Calculado", key="btn_save_markup"):
                info_impostos = f"Imp: {total_impostos_pct:.2f}% | Fixas: {percentual_fixo:.2f}%"
                salvar_simulacao(cnpj_input, "Formação de Preço", custo_direto, preco_venda, margem_desejada, lucro_venda, info_impostos)

    # ==============================================================================
    # ABA 3: ANÁLISE DE MERCADO - PUXA DADOS DA ABA 1
    # ==============================================================================
    with tab_analise:
        st.subheader("🔍 O preço do mercado vale a pena?")
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <small>📡 <b>Dados carregados da Configuração:</b> Custo Fixo: <b>{percentual_fixo:.2f}%</b> | Impostos: <b>{total_impostos_pct:.2f}%</b></small>
        </div>
        """, unsafe_allow_html=True)

        col_m1, col_m2 = st.columns(2)
        preco_mercado = col_m1.number_input("Preço que o Concorrente/Mercado pratica (R$)", value=250.0)
        custo_produto_rev = col_m2.number_input("Seu Custo do Produto (R$)", value=custo_direto) # Puxa padrão da aba anterior
        
        # Cálculo Reverso
        val_impostos = preco_mercado * (total_impostos_pct / 100)
        val_fixas = preco_mercado * (percentual_fixo / 100)
        # Assumindo comissão padrão da aba 2 se não preencher de novo, ou cria campo novo
        val_comissao = preco_mercado * (comissao_pct / 100) 
        
        lucro_real = preco_mercado - custo_produto_rev - val_impostos - val_fixas - val_comissao
        margem_real = (lucro_real / preco_mercado) * 100
        
        st.markdown("### Resultado da Análise")
        
        # Termômetro Visual
        cor_delta = "normal" if margem_real > 0 else "inverse"
        col_a1, col_a2 = st.columns(2)
        col_a1.metric("Lucro Real (R$)", f"R$ {lucro_real:,.2f}")
        col_a2.metric("Margem Real (%)", f"{margem_real:.2f}%", delta=f"{margem_real:.2f}%", delta_color=cor_delta)

        if margem_real < 0:
            st.error("🚨 <b>PREJUÍZO:</b> Com esse preço, você paga para trabalhar. Verifique se seu custo fixo está alto demais para o volume de vendas.")
        elif margem_real < 10:
            st.warning("⚠️ <b>Margem Apertada:</b> Lucro abaixo de 10%. Qualquer imprevisto pode levar ao prejuízo.")
        else:
            st.success("✅ <b>Preço Saudável:</b> A margem é positiva e segura.")

        # Gráfico Waterfall (Cascata) - Perfeito para mostrar onde o dinheiro some
        dados_waterfall = pd.DataFrame({
            "Etapa": ["Preço Venda", "(-) Impostos", "(-) Custo Fixo", "(-) Comissões", "(-) Custo Produto", "(=) Lucro"],
            "Valor": [preco_mercado, -val_impostos, -val_fixas, -val_comissao, -custo_produto_rev, lucro_real]
        })
        
        fig_water = px.bar(dados_waterfall, x="Etapa", y="Valor", text_auto='.2f', title="Cascata de Lucratividade")
        st.plotly_chart(fig_water, use_container_width=True)
        
        if st.button("💾 Salvar Análise de Mercado", key="btn_save_analise"):
            info_impostos = f"Analise Mercado | Imp: {total_impostos_pct:.2f}%"
            salvar_simulacao(cnpj_input, "Análise Mercado", custo_produto_rev, preco_mercado, margem_real, lucro_real, info_impostos)

    # ==============================================================================
    # ABA 4: HISTÓRICO
    # ==============================================================================
    with tab_hist:
        st.subheader("📜 Histórico do Cliente")
        df_hist = carregar_historico(cnpj_input)
        if not df_hist.empty:
            st.dataframe(df_hist.style.format({"custo_produto": "R$ {:.2f}", "preco_venda": "R$ {:.2f}", "margem_pct": "{:.2f}%"}), use_container_width=True)
        else:
            st.info("Nenhum dado gravado para este CNPJ.")

if __name__ == "__main__":
    app()
