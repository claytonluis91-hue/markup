# --- CAMINHO B: EMPRESA EM ANDAMENTO (Módulo de Leitura de XML) ---
elif st.session_state.get('caminho') == 'andamento':
    st.subheader("🔄 Auditoria de Base Histórica")
    st.markdown("Importe os arquivos XML das Notas Fiscais de Saída para construirmos a base de produtos praticados e analisarmos a rentabilidade.")
    
    # O aceitador de arquivos (permite múltiplos)
    arquivos_xml = st.file_uploader("Arraste os XMLs de NF-e aqui", type=["xml"], accept_multiple_files=True)
    
    if arquivos_xml:
        st.success(f"📁 {len(arquivos_xml)} arquivos carregados com sucesso. Processando...")
        
        # Chama o MOTOR para fazer o trabalho pesado
        df_produtos_extraidos = motor.processar_lote_xml(arquivos_xml)
        
        if not df_produtos_extraidos.empty:
            st.markdown("### 📦 Produtos Identificados nas Notas Fiscais")
            st.caption("Esta é a sua base real de vendas. Faltam os Custos de Aquisição para analisarmos o lucro.")
            
            # Exibe a tabela bonitinha no Streamlit
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
