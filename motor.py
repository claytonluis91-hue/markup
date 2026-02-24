import xml.etree.ElementTree as ET
import pandas as pd

# ==========================================
# MÓDULO DE LEITURA DE XML (NF-e Sefaz)
# ==========================================
def processar_lote_xml(lista_arquivos_xml):
    """
    Lê uma lista de arquivos XML (NF-e) carregados pelo Streamlit,
    extrai os produtos, preços de venda e NCM, e retorna um DataFrame.
    """
    lista_produtos = []
    
    # O namespace padrão da Sefaz que sempre vem nos XMLs de NF-e
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    
    for arquivo in lista_arquivos_xml:
        try:
            # Lê o conteúdo do arquivo carregado pelo Streamlit
            tree = ET.parse(arquivo)
            root = tree.getroot()
            
            # Navega por cada item (tag <det>) dentro da nota fiscal
            for det in root.findall('.//nfe:det', ns):
                # Extrai as informações da tag <prod>
                prod = det.find('nfe:prod', ns)
                
                cProd = prod.find('nfe:cProd', ns).text if prod.find('nfe:cProd', ns) is not None else ""
                xProd = prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else ""
                ncm = prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else ""
                cfop = prod.find('nfe:CFOP', ns).text if prod.find('nfe:CFOP', ns) is not None else ""
                uCom = prod.find('nfe:uCom', ns).text if prod.find('nfe:uCom', ns) is not None else ""
                
                # Preço Unitário Comercial (O que o cliente cobrou de fato)
                vUnCom_str = prod.find('nfe:vUnCom', ns).text if prod.find('nfe:vUnCom', ns) is not None else "0"
                vUnCom = float(vUnCom_str)
                
                # Opcional: Pegar o CST/CSOSN do ICMS para saber a tributação exata daquele item
                imposto = det.find('nfe:imposto', ns)
                icms_tag = imposto.find('.//nfe:ICMS/*', ns) if imposto is not None else None
                cst_csosn = ""
                if icms_tag is not None:
                    # Tenta pegar CSOSN (Simples) ou CST (Normal)
                    cst_csosn = icms_tag.find('nfe:CSOSN', ns).text if icms_tag.find('nfe:CSOSN', ns) is not None else \
                                (icms_tag.find('nfe:CST', ns).text if icms_tag.find('nfe:CST', ns) is not None else "")
                
                # Monta o dicionário com a linha do produto
                lista_produtos.append({
                    "Arquivo": arquivo.name,
                    "Código": cProd,
                    "Descrição": xProd,
                    "NCM": ncm,
                    "CFOP": cfop,
                    "Unidade": uCom,
                    "Preço de Venda (R$)": vUnCom,
                    "CST/CSOSN": cst_csosn
                })
                
        except Exception as e:
            # Se um XML vier corrompido, o sistema avisa mas não trava os outros
            print(f"Erro ao processar o arquivo {arquivo.name}: {e}")
            continue

    # Converte a lista de dicionários para uma tabela (DataFrame) do Pandas
    return pd.DataFrame(lista_produtos)
