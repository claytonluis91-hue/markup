import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# MÓDULO DE BANCO DE DADOS
# ==========================================
def conectar_db():
    return sqlite3.connect('precificacao_avancada.db')

def iniciar_banco():
    conn = conectar_db()
    c = conn.cursor()
    # Tabela de Clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (cnpj TEXT PRIMARY KEY, nome TEXT, regime TEXT)''')
    
    # Nova Tabela: Cadastro de Produtos (Preparando para o XML)
    c.execute('''CREATE TABLE IF NOT EXISTS produtos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cnpj TEXT, cProd TEXT, xProd TEXT, ncm TEXT, 
                  custo REAL, preco_venda REAL)''')
    
    conn.commit()
    conn.close()

def buscar_cliente(cnpj):
    conn = conectar_db()
    df = pd.read_sql(f"SELECT * FROM clientes WHERE cnpj = '{cnpj}'", conn)
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None

def salvar_cliente(cnpj, nome, regime):
    conn = conectar_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)', (cnpj, nome, regime))
    conn.commit()
    conn.close()

# ==========================================
# MÓDULO DE CÁLCULOS FISCAIS E FINANCEIROS
# ==========================================
def calcular_markup(custo, impostos_pct, despesas_pct, comissao_pct, lucro_pct):
    """
    Recebe os parâmetros, aplica a regra do Markup Divisor e retorna um dicionário com os resultados.
    """
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

def calcular_margem_real(preco_mercado, custo, impostos_pct, despesas_pct, comissao_pct):
    """
    Faz o caminho inverso para descobrir quanto sobra no bolso.
    """
    deducoes_reais = preco_mercado * ((impostos_pct + despesas_pct + comissao_pct) / 100)
    lucro_real = preco_mercado - custo - deducoes_reais
    margem_pct = (lucro_real / preco_mercado) * 100 if preco_mercado > 0 else 0
    
    return {
        "lucro_real": lucro_real,
        "margem_pct": margem_pct
    }
