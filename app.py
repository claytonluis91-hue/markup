import streamlit as st
import motor  # Importando o nosso "cérebro"

st.set_page_config(page_title="Sistema de Precificação", layout="wide")

# Garante que o banco de dados exista ao abrir o app
motor.iniciar_banco()

st.title("📊 Inteligência em Precificação e Auditoria")
st.markdown("---")

# --- IDENTIFICAÇÃO DO CLIENTE ---
with st.sidebar:
    st.header("🏢 Acesso")
    cnpj_input = st.text_input("CNPJ (Apenas números)")
    
    if cnpj_input:
        cliente_atual = motor.buscar_cliente(cnpj_input)
        if cliente_atual:
            st.success(f"Cliente: {cliente_atual['nome']}")
        else:
            st.warning("Novo CNPJ. Cadastre abaixo.")
            nome_novo = st.text_input("Nome da Empresa")
            regime_novo = st.selectbox("Regime", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
            if st.button("Gravar Cliente"):
                motor.salvar_cliente(cnpj_input, nome_novo, regime_novo)
                st.rerun()

# Trava a tela se não tiver CNPJ
if not cnpj_input:
    st.info("👈 Por favor, inicie informando o CNPJ do cliente na barra lateral.")
    st.stop()

# --- A GRANDE DIVISÃO ---
st.markdown("### Selecione o momento da empresa:")
col1, col2 = st.columns(2)

with col1:
    escolha_zero = st.button("🚀 Empresa do Zero (Planejar Preços)", use_container_width=True)
with col2:
    escolha_andamento = st.button("🔄 Empresa em Andamento (Auditar via XML)", use_container_width=True)

# Guardando a escolha na sessão do Streamlit para a tela não sumir
if escolha_zero:
    st.session_state['caminho'] = 'zero'
if escolha_andamento:
    st.session_state['caminho'] = 'andamento'

st.markdown("---")

# --- CAMINHO A: EMPRESA DO ZERO ---
if st.session_state.get('caminho') == 'zero':
    st.subheader("Simulador de Cenários (Markup)")
    
    c1, c2, c3 = st.columns(3)
    custo = c1.number_input("Custo de Aquisição (R$)", value=100.0)
    impostos = c2.number_input("Carga Tributária (%)", value=18.0)
    lucro = c3.number_input("Margem Desejada (%)", value=20.0)
    
    if st.button("Calcular Preço Ideal"):
        # Chamando o motor para fazer a conta
        resultado = motor.calcular_markup(custo, impostos, despesas_pct=10, comissao_pct=5, lucro_pct=lucro)
        
        if resultado.get("erro"):
            st.error(resultado["erro"])
        else:
            st.success(f"Preço Sugerido: **R$ {resultado['preco_venda']:,.2f}**")
            st.info(f"Lucro Líquido: R$ {resultado['lucro_reais']:,.2f}")

# --- CAMINHO B: EMPRESA EM ANDAMENTO (Módulo de Leitura de XML) ---
elif st.session_state.get('caminho') == 'andamento':
    st.subheader("🔄 Auditoria de Base Histórica")
    st.markdown("Importe os arquivos XML das Notas Fiscais de Saída para construirmos a base de produtos praticados e analisarmos a rentabilidade.")
    
    # O aceitador de arquivos (permite múltiplos)
    arquivos_xml = st.file_uploader("Arraste os XMLs de NF-e aqui", type=["xml"], accept_multiple_files=True)
    
    if arquivos_xml:
        st.success(f"📁 {len(arquivos_xml)} arquivos carregados com sucesso. Processando...")
        
        # Chama o MOTOR para extrair os dados dos XMLs
        df_produtos_extraidos = motor.processar_lote_xml(arquivos_xml)
        
        if not df_produtos_extraidos.empty:
            st.markdown("### 📦 Produtos Identificados nas Notas Fiscais")
            st.caption("Esta é a sua base real de vendas. Faltam os Custos de Aquisição para analisarmos o lucro.")
            
            # Exibe a tabela no Streamlit
            st.dataframe(
                df_produtos_extraidos.style.format({
                    "Preço de Venda (R$)": "R$ {:,.2f}"
                }),
                use_container_width=True
            )
            
            # Próximo passo lógico para a tela:
            st.warning("⚠️ O próximo passo será cruzar estes NCMs com sua tabela de DIFAL e pedir para o cliente preencher o Custo Unitário.")
        else:
            st.error("Não foi possível extrair produtos destes XMLs. Verifique se são NF-e de saída válidas.")
