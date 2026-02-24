import sqlite3
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET

# ==========================================
# MÓDULO DE BANCO DE DADOS E CONFIGURAÇÕES
# ==========================================
def conectar_db():
    return sqlite3.connect('precificacao_avancada.db')

def iniciar_banco():
    """Cria as tabelas necessárias para o sistema funcionar."""
    conn = conectar_db()
    c = conn.cursor()
    # Tabela de Clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (cnpj TEXT PRIMARY KEY, nome TEXT, regime TEXT)''')
    
    # Tabela de Produtos (preparada para os XMLs)
    c.execute('''CREATE TABLE IF NOT EXISTS produtos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cnpj TEXT, cProd TEXT, xProd TEXT, ncm TEXT, 
                  custo REAL, preco_venda REAL)''')
    
    conn.commit()
    conn.close()

def buscar_cliente(cnpj):
    """Busca o cadastro do cliente pelo CNPJ."""
    conn = conectar_db()
    df = pd.read_sql(f"SELECT * FROM clientes WHERE cnpj = '{cnpj}'", conn)
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

def salvar_cliente(cnpj, nome, regime):
    """Salva ou atualiza um cliente no banco."""
    conn = conectar_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)', (cnpj, nome, regime))
    conn.commit()
    conn.close()

# ==========================================
# MÓDULO DE CÁLCULOS FISCAIS E FINANCEIROS
# ==========================================
def calcular_markup(custo, impostos_pct, despesas_pct, comissao_pct, lucro_pct):
    """Calcula o preço de venda ideal usando Markup Divisor."""
    total_deducoes = impostos_pct + despesas_pct + comissao_pct + lucro_pct
    
    if total_deducoes >= 100:
        return {"erro": "Deduções ultrapassam 100%. Cálculo impossível."}
    
    divisor = (100 - total_deducoes) / 100
    preco_venda = custo / divisor
    lucro_reais = preco_venda * (lucro_pct / 100)
    
    return {
        "erro": None,
        "preco_venda": preco_venda,
        "lucro_reais": lucro_reais,
        "markup_multiplicador": preco_venda / custo if custo > 0 else 0
    }

# ==========================================
# MÓDULO DE LEITURA DE XML (NF-e Sefaz)
# ==========================================
def processar_lote_xml(lista_arquivos_xml):
    """Lê os XMLs de NF-e e extrai NCMs, CFOPs e Preços."""
    lista_produtos = []
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    for arquivo in lista_arquivos_xml:
        try:
            tree = ET.parse(arquivo)
            root = tree.getroot()
            
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                
                cProd = prod.find('nfe:cProd', ns).text if prod.find('nfe:cProd', ns) is not None else ""
                xProd = prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else ""
                ncm = prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else ""
                cfop = prod.find('nfe:CFOP', ns).text if prod.find('nfe:CFOP', ns) is not None else ""
                uCom = prod.find('nfe:uCom', ns).text if prod.find('nfe:uCom', ns) is not None else ""
                
                vUnCom_str = prod.find('nfe:vUnCom', ns).text if prod.find('nfe:vUnCom', ns) is not None else "0"
                vUnCom = float(vUnCom_str)
                
                lista_produtos.append({
                    "Arquivo": arquivo.name,
                    "Código": cProd,
                    "Descrição": xProd,
                    "NCM": ncm,
                    "CFOP": cfop,
                    "Unidade": uCom,
                    "Preço de Venda (R$)": vUnCom
                })
        except Exception as e:
            print(f"Erro ao processar o arquivo {arquivo.name}: {e}")
            continue

    return pd.DataFrame(lista_produtos)
