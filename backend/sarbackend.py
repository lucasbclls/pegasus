from flask import Flask, request, jsonify
import pyodbc
import pandas as pd
import requests
from datetime import datetime
import re
from flask_cors import cross_origin, CORS
from threading import Thread
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from functools import lru_cache
import asyncio
import aiohttp
import json
from queue import Queue
import threading

app = Flask(__name__)
# Configuração CORS global
CORS(app)

# Configurações
EXCEL_PATH = r'C:\Users\Paulo Lucas\OneDrive - Claro SA\USER-DTC_HE_INFRA - ES - Documentos\Acionamento Datacenter_Headend ES1.xlsx'
SAR_EXCEL_PATH = r'C:\Users\Paulo Lucas\OneDrive - Claro SA\USER-DTC_HE_INFRA - ES - Documentos\Execucao_SAR_ES1.xlsx'
ABA = 'Sheet1'
REDMINE_URL = "http://187.36.193.239/redmine/issues"
API_KEY = "df3745b4f0356e84781e4254d109efd3e31e0eb6"
HEADERS = {"Content-Type": "application/json", "X-Redmine-API-Key": API_KEY}

# Pool de conexões para requests
session = requests.Session()
session.headers.update(HEADERS)

# Pool de threads para operações assíncronas
executor = ThreadPoolExecutor(max_workers=10)

# Cache para evitar leituras desnecessárias do Excel
excel_cache = {}
excel_cache_time = 0
CACHE_DURATION = 60

# Pool otimizado de conexões do banco
connection_pool = Queue(maxsize=10)
connection_lock = threading.Lock()

def init_connection_pool():
    """Pool otimizado com retry e validação"""
    global connection_pool
    for i in range(10):
        try:
            conn = pyodbc.connect(
                'DRIVER={SQL Server};'
                'SERVER=localhost;'
                'DATABASE=powerbi;'
                'Trusted_Connection=yes;'
                'Connection Timeout=30;'
                'Command Timeout=30;'
            )
            # Testa a conexão
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            connection_pool.put(conn)
            logging.info(f"Conexão {i+1} criada e testada com sucesso")
        except Exception as e:
            logging.error(f"Erro ao criar conexão {i+1}: {e}")

def create_new_connection():
    """Cria nova conexão quando o pool está vazio"""
    return pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=localhost;'
        'DATABASE=powerbi;'
        'Trusted_Connection=yes;'
        'Connection Timeout=30;'
        'Command Timeout=30;'
    )

def get_connection():
    """Obtém conexão com timeout e retry"""
    try:
        conn = connection_pool.get(timeout=5)
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return conn
        except Exception as e:
            logging.warning(f"Conexão inválida do pool, criando nova: {e}")
            try:
                conn.close()
            except Exception as close_e:
                logging.error(f"Erro ao fechar conexão inválida: {close_e}")
            return create_new_connection()
            
    except Exception as e:
        logging.warning(f"Pool vazio ou timeout, criando nova conexão: {e}")
        return create_new_connection()

def return_connection(conn):
    """Retorna conexão para o pool com validação"""
    try:
        if connection_pool.qsize() < connection_pool.maxsize:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection_pool.put(conn)
        else:
            conn.close()
    except Exception as e:
        logging.warning(f"Conexão inválida ao retornar para o pool, fechando: {e}")
        try:
            conn.close()
        except Exception as close_e:
            logging.error(f"Erro ao fechar conexão inválida ao retornar: {close_e}")

@lru_cache(maxsize=100)
def get_cached_excel_data():
    """Cache dos dados do Excel com TTL"""
    global excel_cache, excel_cache_time
    current_time = time.time()
    
    if current_time - excel_cache_time > CACHE_DURATION:
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=ABA)
            df.columns = [re.sub(r'[:\s]+$', '', col.strip().lower()) for col in df.columns]
            excel_cache = df.to_dict('records')
            excel_cache_time = current_time
        except Exception as e:
            logging.error(f"Erro ao ler Excel: {e}")
            return None
    
    return excel_cache

def update_excel_optimized(chamado_id, novo_status, responsavel=None):
    """Excel otimizado com cache inteligente e gravação direta"""
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=ABA)
        df.columns = [re.sub(r'[:\s]+$', '', col.strip().lower()) for col in df.columns]
        
        if 'id' not in df.columns:
            logging.error("Coluna 'id' não encontrada no Excel.")
            return False

        mask = df['id'] == chamado_id
        if not mask.any():
            logging.warning(f"Chamado {chamado_id} não encontrado no Excel para atualização.")
            return False
            
        if novo_status and 'status' in df.columns:
            df.loc[mask, 'status'] = novo_status
        
        if responsavel is not None and 'responsavel' in df.columns:
            df.loc[mask, 'responsavel'] = responsavel
        
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=ABA, index=False)
        
        global excel_cache_time
        excel_cache_time = 0
        get_cached_excel_data.cache_clear()
        
        return True
        
    except Exception as e:
        logging.error(f"Erro ao atualizar Excel para chamado {chamado_id}: {e}")
        return False

def update_excel_sar_optimized(sar_id, novo_status, responsavel=None):
    """Excel otimizado para SARs"""
    try:
        df = pd.read_excel(SAR_EXCEL_PATH, sheet_name=ABA)
        df.columns = [re.sub(r'[:\s]+$', '', col.strip().lower()) for col in df.columns]
        
        # Para a tabela ExecucaoSar, vamos usar NumSar como identificador
        if 'numsar' not in df.columns:
            logging.error("Coluna 'numsar' não encontrada no Excel de SARs.")
            return False

        mask = df['numsar'] == sar_id
        if not mask.any():
            logging.warning(f"SAR {sar_id} não encontrado no Excel para atualização.")
            return False
            
        if novo_status and 'status' in df.columns:
            df.loc[mask, 'status'] = novo_status
        
        if responsavel is not None and 'responsaveldtc' in df.columns:
            df.loc[mask, 'responsaveldtc'] = responsavel
        
        with pd.ExcelWriter(SAR_EXCEL_PATH, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=ABA, index=False)
        
        return True
        
    except Exception as e:
        logging.error(f"Erro ao atualizar Excel para SAR {sar_id}: {e}")
        return False

def update_redmine_optimized(item_id, status_id=None, notes=None, assignee_id=None):
    """Redmine otimizado com retry e timeout"""
    max_retries = 2
    timeout = 15
    
    for attempt in range(max_retries):
        try:
            url = f"{REDMINE_URL}/{item_id}.json"
            payload = {"issue": {}}
            
            if status_id:
                payload["issue"]["status_id"] = status_id
            if notes:
                payload["issue"]["notes"] = notes
            if assignee_id is not None:
                payload["issue"]["assigned_to_id"] = assignee_id
            
            response = session.put(url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                logging.warning(f"Item {item_id} não encontrado no Redmine (código 404).")
                return True
            else:
                logging.warning(f"Redmine retornou {response.status_code} para item {item_id}, tentativa {attempt + 1}. Resposta: {response.text}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout ao atualizar Redmine para item {item_id} (tentativa {attempt + 1}).")
            if attempt == max_retries - 1:
                return False
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erro inesperado ao atualizar Redmine para item {item_id} (tentativa {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(1)
    
    return False

def update_database_optimized(chamado_id, operation_type, observacoes=None, campos_atualizacao=None):
    """Operação de banco otimizada com prepared statement e suporte a observações/atualização genérica para CHAMADOS"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if operation_type == 'delete':
            cursor.execute("DELETE FROM dbo.[GRC-Chamados] WHERE ID = ?", (chamado_id,))
        elif operation_type == 'update_observacoes':
            cursor.execute(
                "UPDATE dbo.[GRC-Chamados] SET Observacoes = ? WHERE ID = ?", 
                (observacoes, chamado_id)
            )
        elif operation_type == 'check_status':
            cursor.execute("SELECT COUNT(*) FROM dbo.[GRC-Chamados] WHERE ID = ?", (chamado_id,))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        elif operation_type == 'get_observacoes':
            cursor.execute("SELECT Observacoes FROM dbo.[GRC-Chamados] WHERE ID = ?", (chamado_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else ""
        elif operation_type == 'get_responsavel':
            cursor.execute("SELECT Responsavel FROM dbo.[GRC-Chamados] WHERE ID = ?", (chamado_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        elif operation_type == 'generic_update' and campos_atualizacao:
            campos_filtrados = {k: v for k, v in campos_atualizacao.items() if v is not None or k == 'Responsavel'}
            
            if campos_filtrados:
                set_clauses = [f"[{k}] = ?" for k in campos_filtrados.keys()]
                values = list(campos_filtrados.values())
                query = f"UPDATE dbo.[GRC-Chamados] SET {', '.join(set_clauses)} WHERE ID = ?"
                cursor.execute(query, (*values, chamado_id))

        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"Erro na operação de banco para chamado {chamado_id} (tipo: {operation_type}): {e}")
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_e:
                logging.error(f"Erro ao tentar rollback: {rollback_e}")
        return False
    finally:
        if conn:
            return_connection(conn)

# ============= FUNÇÕES AUXILIARES PARA SARs =============

def update_database_sar_optimized(sar_identifier, operation_type, observacoes=None, campos_atualizacao=None):
    """Operação de banco otimizada para SARs - usando NumSar como identificador"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if operation_type == 'delete':
            cursor.execute("DELETE FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (sar_identifier,))
        elif operation_type == 'update_observacoes':
            # Como a tabela não tem campo Observacoes, vamos adicionar no Caminho ou criar um campo
            cursor.execute(
                "UPDATE dbo.[ExecucaoSar] SET Caminho = ? WHERE NumSar = ?", 
                (observacoes, sar_identifier)
            )
        elif operation_type == 'check_status':
            cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (sar_identifier,))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        elif operation_type == 'get_observacoes':
            cursor.execute("SELECT Caminho FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (sar_identifier,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else ""
        elif operation_type == 'get_responsavel':
            cursor.execute("SELECT ResponsavelDTC FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (sar_identifier,))
            result = cursor.fetchone()
            return result[0] if result else None
        elif operation_type == 'generic_update' and campos_atualizacao:
            # Mapear campos do frontend para os campos da tabela real
            campos_mapeados = {}
            for k, v in campos_atualizacao.items():
                if k == 'responsavel':
                    campos_mapeados['ResponsavelDTC'] = v
                elif k == 'status':
                    campos_mapeados['Status'] = v
                elif k == 'observacoes':
                    campos_mapeados['Caminho'] = v
                else:
                    # Manter outros campos como estão se existirem na tabela
                    campos_mapeados[k] = v
            
            campos_filtrados = {k: v for k, v in campos_mapeados.items() if v is not None or k == 'ResponsavelDTC'}
            
            if campos_filtrados:
                set_clauses = [f"[{k}] = ?" for k in campos_filtrados.keys()]
                values = list(campos_filtrados.values())
                query = f"UPDATE dbo.[ExecucaoSar] SET {', '.join(set_clauses)} WHERE NumSar = ?"
                cursor.execute(query, (*values, sar_identifier))

        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"Erro na operação de banco para SAR {sar_identifier} (tipo: {operation_type}): {e}")
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_e:
                logging.error(f"Erro ao tentar rollback: {rollback_e}")
        return False
    finally:
        if conn:
            return_connection(conn)

def verificar_status_sar(sar_identifier):
    """Verifica se o SAR está ativo (não fechado/cancelado)"""
    return update_database_sar_optimized(sar_identifier, 'check_status')

def obter_observacoes_sar_db(sar_identifier):
    """Obtém as observações do SAR do banco de dados"""
    return update_database_sar_optimized(sar_identifier, 'get_observacoes')

# Funções utilitárias
def obter_observacoes_chamado(chamado_id):
    """Obtém as observações do chamado do banco de dados"""
    return update_database_optimized(chamado_id, 'get_observacoes')

def salvar_observacoes_chamado(chamado_id, observacoes):
    """Salva as observações do chamado no banco de dados"""
    return update_database_optimized(chamado_id, 'update_observacoes', observacoes=observacoes)

def verificar_status_chamado(chamado_id):
    """Verifica se o chamado está ativo (não fechado/cancelado)"""
    return update_database_optimized(chamado_id, 'check_status')

def formatar_observacao(usuario, observacao):
    """Formata uma nova observação com timestamp e usuário"""
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"[{data_hora} - {usuario}]: {observacao}"

# ============= ROTAS PRINCIPAIS PARA CHAMADOS =============

@app.route("/api/chamados", methods=["GET", "OPTIONS"])
@cross_origin(methods=["GET", "OPTIONS"], supports_credentials=True)
def listar_chamados():
    """Lista todos os chamados para o frontend pai"""
    if request.method == "OPTIONS":
        return '', 200
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'GRC-Chamados' 
            ORDER BY ORDINAL_POSITION
        """)
        
        colunas_existentes = [row[0] for row in cursor.fetchall()]
        logging.info(f"📋 Colunas encontradas na tabela: {colunas_existentes}")
        
        cursor.execute("SELECT * FROM dbo.[GRC-Chamados] ORDER BY ID DESC")
        resultados = cursor.fetchall()
        
        chamados = []
        for row in resultados:
            chamado = {}
            
            for i, coluna in enumerate(colunas_existentes):
                valor = row[i] if i < len(row) else None
                chamado[coluna] = valor if valor is not None else ''
            
            chamado_padronizado = {
                'id': chamado.get('ID', ''),
                'nomeSolicitante': chamado.get('nomeSolicitante', chamado.get('NomeSolicitante', chamado.get('nome_solicitante', ''))),
                'telefone': chamado.get('telefone', chamado.get('Telefone', '')),
                'emailSolicitante': chamado.get('emailSolicitante', chamado.get('EmailSolicitante', chamado.get('email_solicitante', ''))),
                'empresa': chamado.get('empresa', chamado.get('Empresa', '')),
                'cidade': chamado.get('cidade', chamado.get('Cidade', '')),
                'tecnologia': chamado.get('tecnologia', chamado.get('Tecnologia', '')),
                'nodeAfetadas': chamado.get('nodeAfetadas', chamado.get('NodeAfetadas', chamado.get('node_afetadas', ''))),
                'tipoReclamacao': chamado.get('tipoReclamacao', chamado.get('TipoReclamacao', chamado.get('tipo_reclamacao', ''))),
                'detalhesProblema': chamado.get('detalhesProblema', chamado.get('DetalhesProblema', chamado.get('detalhes_problema', ''))),
                'testesRealizados': chamado.get('testesRealizados', chamado.get('TestesRealizados', chamado.get('testes_realizados', ''))),
                'modelEquipamento': chamado.get('modelEquipamento', chamado.get('ModelEquipamento', chamado.get('model_equipamento', ''))),
                'baseAfetada': chamado.get('baseAfetada', chamado.get('BaseAfetada', chamado.get('base_afetada', ''))),
                'contratosAfetados': chamado.get('contratosAfetados', chamado.get('ContratosAfetados', chamado.get('contratos_afetados', ''))),
                'servicoAfetado': chamado.get('servicoAfetado', chamado.get('ServicoAfetado', chamado.get('servico_afetado', ''))),
                'dataEvento': chamado.get('dataEvento', chamado.get('DataEvento', chamado.get('data_evento', ''))),
                'horaInicio': chamado.get('horaInicio', chamado.get('HoraInicio', chamado.get('hora_inicio', ''))),
                'horaConclusao': chamado.get('horaConclusao', chamado.get('HoraConclusao', chamado.get('hora_conclusao', ''))),
                'status': chamado.get('status', chamado.get('Status', 'Pendente')),
                'prioridade': chamado.get('prioridade', chamado.get('Prioridade', 'Baixa')),
                'responsavel': chamado.get('responsavel', chamado.get('Responsavel', '')),
                'observacoes': chamado.get('observacoes', chamado.get('Observacoes', ''))
            }
            
            chamados.append(chamado_padronizado)
        
        cursor.close()
        
        logging.info(f"✅ Listando {len(chamados)} chamados para o frontend")
        return jsonify(chamados), 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar chamados: {e}")
        return jsonify({"erro": str(e)}), 500
    finally:
        if conn:
            return_connection(conn)

# ============= ROTAS PARA SARs =============

@app.route("/api/sars", methods=["GET", "OPTIONS"])
@cross_origin(methods=["GET", "OPTIONS"], supports_credentials=True)
def listar_sars():
    """Lista todos os SARs para o frontend"""
    if request.method == "OPTIONS":
        return '', 200
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query para a tabela real ExecucaoSar
        cursor.execute("SELECT * FROM dbo.[ExecucaoSar] ORDER BY DataSolicitacao DESC")
        resultados = cursor.fetchall()
        
        # Obter nomes das colunas
        colunas = [description[0] for description in cursor.description]
        logging.info(f"📋 Colunas encontradas na tabela ExecucaoSar: {colunas}")
        
        sars = []
        for row in resultados:
            sar_dict = {}
            
            # Mapear valores das colunas
            for i, coluna in enumerate(colunas):
                valor = row[i] if i < len(row) else None
                sar_dict[coluna] = valor if valor is not None else ''
            
            # Padronizar para o frontend usando os campos reais da tabela
            sar_padronizado = {
                'id': sar_dict.get('NumSar', ''),  # Usar NumSar como ID
                'numeroSar': sar_dict.get('NumSar', ''),
                'dataSolicitacao': sar_dict.get('DataSolicitacao', ''),
                'cidade': sar_dict.get('Cidade', ''),
                'acao': sar_dict.get('Acao', ''),
                'areaTecnica': sar_dict.get('AreaTecnica', ''),
                'designacao': sar_dict.get('Designacao', ''),
                'enderecoNap': sar_dict.get('EnderecoNap', ''),
                'quantPort': sar_dict.get('QuantPort', 0),
                'caminho': sar_dict.get('Caminho', ''),
                'status': sar_dict.get('Status', 'Pendente'),
                'responsavelHub': sar_dict.get('ResponsavelHub', ''),
                'dataVenc': sar_dict.get('DataVenc', ''),
                'dataExecucao': sar_dict.get('DataExecucao', ''),
                'dataCancelamento': sar_dict.get('DataCancelamento', ''),
                'idadeExecucao': sar_dict.get('IdadeExecucao', 0),
                'anoMes': sar_dict.get('AnoMes', ''),
                'responsavelDTC': sar_dict.get('ResponsavelDTC', ''),
                'idRedmine': sar_dict.get('ID_redmine', 0),
                
                # Campos adicionais para compatibilidade com o frontend
                'responsavel': sar_dict.get('ResponsavelDTC', ''),
                'prioridade': 'Normal',  # Campo não existe na tabela, usar padrão
                'tipoServico': sar_dict.get('Acao', ''),
                'cliente': sar_dict.get('Designacao', ''),
                'endereco': sar_dict.get('EnderecoNap', ''),
                'tecnologia': sar_dict.get('AreaTecnica', ''),
                'descricaoServico': sar_dict.get('Caminho', ''),
                'observacoes': sar_dict.get('Caminho', ''),  # Usando Caminho como observações
            }
            
            sars.append(sar_padronizado)
        
        cursor.close()
        
        logging.info(f"✅ Listando {len(sars)} SARs para o frontend")
        return jsonify(sars), 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar SARs: {e}")
        return jsonify({"erro": str(e)}), 500
    finally:
        if conn:
            return_connection(conn)

@app.route("/api/sars/<sar_id>", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def atualizar_sar_api(sar_id):
    """Endpoint /api/sars/:id para compatibilidade com o frontend"""
    if request.method == "OPTIONS":
        return '', 200
    
    dados = request.get_json()
    logging.info(f"✅ Atualizando SAR {sar_id} via API com dados: {dados}")
    
    try:
        success = update_database_sar_optimized(sar_id, 'generic_update', campos_atualizacao=dados)
        
        if success:
            if 'status' in dados:
                novo_status = dados['status']
                responsavel = dados.get('responsavel')
                
                def update_secondary_systems():
                    try:
                        status_map = {
                            'Pendente': 1,
                            'Em Andamento': 2, 
                            'Concluído': 5,
                            'Cancelado': 6
                        }
                        
                        excel_future = executor.submit(update_excel_sar_optimized, sar_id, novo_status, responsavel)
                        
                        # Se existe ID_redmine, atualizar no Redmine
                        redmine_id = dados.get('idRedmine', 0)
                        if redmine_id and redmine_id > 0:
                            redmine_future = executor.submit(update_redmine_optimized, redmine_id, status_map.get(novo_status, 1))
                            redmine_result = redmine_future.result(timeout=30)
                        else:
                            redmine_result = True
                        
                        excel_result = excel_future.result(timeout=30)
                        
                        logging.info(f"SAR {sar_id} atualizado via API - Excel: {excel_result}, Redmine: {redmine_result}")
                        
                    except Exception as e:
                        logging.error(f"Erro ao atualizar sistemas secundários para SAR {sar_id}: {e}")
                
                executor.submit(update_secondary_systems)
            
            return jsonify({
                "success": True,
                "mensagem": f"SAR {sar_id} atualizado com sucesso"
            }), 200
        else:
            return jsonify({"erro": "Falha ao atualizar SAR no banco de dados"}), 500
            
    except Exception as e:
        logging.error(f"Erro ao atualizar SAR via API: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/sars/<sar_id>/assumir", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def assumir_sar_endpoint(sar_id):
    """Assumir SAR com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200

    data = request.get_json() or {}
    responsavel = data.get("responsavel")
    apenas_visual = data.get("apenas_visual", False)

    if not responsavel:
        return jsonify({"erro": "Responsável não fornecido."}), 400

    try:
        if not verificar_status_sar(sar_id):
            return jsonify({"erro": "SAR não encontrado."}), 404
        
        responsavel_atual = update_database_sar_optimized(sar_id, 'get_responsavel')
        
        if responsavel_atual and responsavel_atual.strip():
            if responsavel_atual.strip() != responsavel.strip():
                return jsonify({
                    "erro": f"SAR já foi assumido por {responsavel_atual}",
                    "responsavel_atual": responsavel_atual,
                    "conflito": True
                }), 409
            else:
                return jsonify({
                    "success": True,
                    "mensagem": f"SAR já estava assumido por {responsavel}",
                    "responsavel_atual": responsavel,
                    "responsavel_nome": responsavel,
                    "ja_assumido": True,
                    "apenas_visual": apenas_visual
                }), 200
            
        db_success = update_database_sar_optimized(sar_id, 'generic_update', campos_atualizacao={'responsavel': responsavel})
        
        if not db_success:
            return jsonify({"erro": "Erro ao assumir o SAR no banco."}), 500

        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_sar_optimized(sar_id, None, responsavel)
                    logging.info(f"SAR {sar_id} assumido - Excel: {excel_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para SAR {sar_id}: {e}")

            executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"SAR assumido por {responsavel}",
            "responsavel_atual": responsavel,
            "responsavel_nome": responsavel,
            "apenas_visual": apenas_visual,
            "primeira_vez": True
        }

        logging.info(f"✅ SAR {sar_id} assumido por {responsavel} (apenas_visual: {apenas_visual})")
        return jsonify(response_data), 200

    except Exception as e:
        logging.error(f"Erro ao assumir SAR {sar_id}: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/sars/<sar_id>/liberar', methods=['PUT', 'OPTIONS'])
@cross_origin(methods=['PUT', 'OPTIONS'], supports_credentials=True)
def liberar_sar_endpoint(sar_id):
    """Liberar SAR com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        apenas_visual = data.get("apenas_visual", False)
        
        if not verificar_status_sar(sar_id):
            return jsonify({"erro": "SAR não encontrado."}), 404

        db_success = update_database_sar_optimized(sar_id, 'generic_update', campos_atualizacao={'responsavel': None})
        
        if not db_success:
            return jsonify({"erro": "Erro ao liberar o SAR no banco."}), 500

        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_sar_optimized(sar_id, None, None)
                    logging.info(f"SAR {sar_id} liberado - Excel: {excel_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para SAR {sar_id}: {e}")

            executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": "SAR liberado com sucesso!",
            "responsavel_atual": None,
            "apenas_visual": apenas_visual,
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }

        logging.info(f"✅ SAR {sar_id} liberado (apenas_visual: {apenas_visual})")
        return jsonify(response_data), 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"Erro ao liberar SAR {sar_id} (tempo: {tempo_erro:.2f}s): {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

@app.route("/sars/<sar_id>/finalizar", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def finalizar_sar(sar_id):
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        if not verificar_status_sar(sar_id):
            return jsonify({"erro": "SAR não encontrado"}), 404

        # Atualizar status para Concluído ao invés de deletar
        db_success = update_database_sar_optimized(sar_id, 'generic_update', campos_atualizacao={
            'status': 'Concluído',
            'DataExecucao': datetime.now()
        })
        
        if not db_success:
            return jsonify({"erro": "Erro ao finalizar SAR no banco"}), 500

        def update_external_systems():
            try:
                excel_result = update_excel_sar_optimized(sar_id, 'Concluído')
                logging.info(f"SAR {sar_id} finalizado - Excel: {excel_result}")
            except Exception as e:
                logging.error(f"Erro ao atualizar sistemas externos para SAR {sar_id}: {e}")

        executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"SAR {sar_id} finalizado com sucesso",
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }
        
        logging.info(f"✅ SAR {sar_id} finalizado com sucesso")
        return jsonify(response_data), 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"Erro crítico ao finalizar SAR {sar_id} (tempo: {tempo_erro:.2f}s): {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

@app.route("/sars/<sar_id>/observacoes", methods=["GET", "OPTIONS"])
@cross_origin(origin="http://localhost:5173", methods=["GET", "OPTIONS"], supports_credentials=True)
def obter_observacoes_sar(sar_id):
    """Obtém todas as observações de um SAR"""
    if request.method == "OPTIONS":
        return '', 200

    try:
        if not verificar_status_sar(sar_id):
            return jsonify({"erro": "SAR não encontrado"}), 404

        observacoes_raw = obter_observacoes_sar_db(sar_id)
        
        observacoes_lista = []
        if observacoes_raw:
            observacoes_split = observacoes_raw.split('\n\n')
            
            for obs in observacoes_split:
                obs = obs.strip()
                if obs:
                    match = re.match(r'\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2}) - ([^\]]+)\]: (.+)', obs, re.DOTALL)
                    if match:
                        data_str, usuario, conteudo = match.groups()
                        observacoes_lista.append({
                            'data': data_str,
                            'usuario': usuario,
                            'observacao': conteudo.strip(),
                            'timestamp': datetime.strptime(data_str, "%d/%m/%Y %H:%M").isoformat()
                        })
                    else:
                        observacoes_lista.append({
                            'data': 'Data não disponível',
                            'usuario': 'Sistema',
                            'observacao': obs,
                            'timestamp': datetime.now().isoformat()
                        })

        return jsonify({
            "success": True,
            "observacoes": observacoes_lista,
            "total": len(observacoes_lista)
        })

    except Exception as e:
        logging.error(f"Erro ao obter observações do SAR: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/sars/<sar_id>/observacao", methods=["PUT", "OPTIONS"])
@cross_origin(origin="http://localhost:5173", methods=["PUT", "OPTIONS"], supports_credentials=True)
def adicionar_observacao_sar(sar_id):
    """Adiciona uma nova observação ao SAR"""
    if request.method == "OPTIONS":
        return '', 200

    try:
        dados = request.get_json()
        nova_obs = dados.get("observacao", "")
        usuario = dados.get("usuario", "Sistema")
        
        if isinstance(nova_obs, str):
            nova_obs = nova_obs.strip()
        else:
            nova_obs = str(nova_obs).strip() if nova_obs else ""
            
        if isinstance(usuario, str):
            usuario = usuario.strip()
        else:
            usuario = str(usuario).strip() if usuario else "Sistema"
        
        if not nova_obs:
            return jsonify({"erro": "Observação não pode estar vazia"}), 400

        if not verificar_status_sar(sar_id):
            return jsonify({"erro": "SAR não encontrado ou já finalizado"}), 404

        observacoes_existentes = obter_observacoes_sar_db(sar_id)
        
        nova_observacao_formatada = formatar_observacao(usuario, nova_obs)
        
        if observacoes_existentes:
            observacoes_atualizadas = f"{observacoes_existentes}\n\n{nova_observacao_formatada}"
        else:
            observacoes_atualizadas = nova_observacao_formatada

        if not update_database_sar_optimized(sar_id, 'update_observacoes', observacoes=observacoes_atualizadas):
            return jsonify({"erro": "Erro ao salvar observação no banco"}), 500

        # Atualizar no Redmine se houver ID_redmine
        def update_redmine_background():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT ID_redmine FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (sar_id,))
                result = cursor.fetchone()
                cursor.close()
                return_connection(conn)
                
                if result and result[0] and result[0] > 0:
                    return update_redmine_optimized(result[0], notes=f"[{usuario}] {nova_obs}")
                return True
            except Exception as e:
                logging.error(f"Erro ao atualizar Redmine para SAR {sar_id}: {e}")
                return False
        
        executor.submit(update_redmine_background)

        return jsonify({
            "success": True,
            "mensagem": "Observação adicionada com sucesso",
            "observacao": {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario": usuario,
                "observacao": nova_obs,
                "timestamp": datetime.now().isoformat()
            }
        }), 201

    except Exception as e:
        logging.error(f"Erro ao adicionar observação ao SAR: {e}")
        return jsonify({"erro": str(e)}), 500

# ============= ROTAS DE ATUALIZAÇÃO DE CHAMADOS =============

@app.route("/api/chamados/<int:id>", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def atualizar_chamado_api(id):
    """Endpoint /api/chamados/:id para compatibilidade com o frontend pai"""
    if request.method == "OPTIONS":
        return '', 200
    
    dados = request.get_json()
    logging.info(f"✅ Atualizando chamado {id} via API com dados: {dados}")
    
    try:
        success = update_database_optimized(id, 'generic_update', campos_atualizacao=dados)
        
        if success:
            if 'status' in dados:
                novo_status = dados['status']
                responsavel = dados.get('responsavel')
                
                def update_secondary_systems():
                    try:
                        status_map = {
                            'Pendente': 1,
                            'Em Andamento': 2, 
                            'Concluído': 5,
                            'Cancelado': 6
                        }
                        
                        excel_future = executor.submit(update_excel_optimized, id, novo_status, responsavel)
                        redmine_future = executor.submit(update_redmine_optimized, id, status_map.get(novo_status, 1))
                        
                        excel_result = excel_future.result(timeout=30)
                        redmine_result = redmine_future.result(timeout=30)
                        
                        logging.info(f"Chamado {id} atualizado via API - Excel: {excel_result}, Redmine: {redmine_result}")
                        
                    except Exception as e:
                        logging.error(f"Erro ao atualizar sistemas secundários para chamado {id}: {e}")
                
                executor.submit(update_secondary_systems)
            
            return jsonify({
                "success": True,
                "mensagem": f"Chamado {id} atualizado com sucesso"
            }), 200
        else:
            return jsonify({"erro": "Falha ao atualizar chamado no banco de dados"}), 500
            
    except Exception as e:
        logging.error(f"Erro ao atualizar chamado via API: {e}")
        return jsonify({"erro": str(e)}), 500

# ============= ROTAS DE RESPONSÁVEL PARA CHAMADOS =============

@app.route("/chamados/<int:id>/assumir", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def assumir_chamado_endpoint(id):
    """Assumir chamado com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200

    data = request.get_json() or {}
    responsavel = data.get("responsavel")
    apenas_visual = data.get("apenas_visual", False)

    if not responsavel:
        return jsonify({"erro": "Responsável não fornecido."}), 400

    try:
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado."}), 404
        
        responsavel_atual = update_database_optimized(id, 'get_responsavel')
        
        if responsavel_atual and responsavel_atual.strip():
            if responsavel_atual.strip() != responsavel.strip():
                return jsonify({
                    "erro": f"Chamado já foi assumido por {responsavel_atual}",
                    "responsavel_atual": responsavel_atual,
                    "conflito": True
                }), 409
            else:
                return jsonify({
                    "success": True,
                    "mensagem": f"Chamado já estava assumido por {responsavel}",
                    "responsavel_atual": responsavel,
                    "responsavel_nome": responsavel,
                    "ja_assumido": True,
                    "apenas_visual": apenas_visual
                }), 200
            
        db_success = update_database_optimized(id, 'generic_update', campos_atualizacao={'Responsavel': responsavel})
        
        if not db_success:
            return jsonify({"erro": "Erro ao assumir o chamado no banco."}), 500

        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(id, None, responsavel)
                    redmine_result = update_redmine_optimized(id, assignee_id=1)
                    logging.info(f"Chamado {id} assumido - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

            executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"Chamado assumido por {responsavel}",
            "responsavel_atual": responsavel,
            "responsavel_nome": responsavel,
            "apenas_visual": apenas_visual,
            "primeira_vez": True
        }

        logging.info(f"✅ Chamado {id} assumido por {responsavel} (apenas_visual: {apenas_visual})")
        return jsonify(response_data), 200

    except Exception as e:
        logging.error(f"Erro ao assumir chamado {id}: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/chamados/<int:id>/liberar', methods=['PUT', 'OPTIONS'])
@cross_origin(methods=['PUT', 'OPTIONS'], supports_credentials=True)
def liberar_chamado_endpoint(id):
    """Liberar chamado com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        apenas_visual = data.get("apenas_visual", False)
        
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado."}), 404

        db_success = update_database_optimized(id, 'generic_update', campos_atualizacao={'Responsavel': None})
        
        if not db_success:
            return jsonify({"erro": "Erro ao liberar o chamado no banco."}), 500

        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(id, None, None)
                    redmine_result = update_redmine_optimized(id, assignee_id=None)
                    logging.info(f"Chamado {id} liberado - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

            executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": "Chamado liberado com sucesso!",
            "responsavel_atual": None,
            "apenas_visual": apenas_visual,
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }

        logging.info(f"✅ Chamado {id} liberado (apenas_visual: {apenas_visual})")
        return jsonify(response_data), 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"Erro ao liberar chamado {id} (tempo: {tempo_erro:.2f}s): {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ============= ROTAS DE FINALIZAÇÃO E CANCELAMENTO PARA CHAMADOS =============

@app.route("/chamados/<int:id>/finalizar", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def finalizar_chamado(id):
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado"}), 404

        db_success = update_database_optimized(id, 'delete')
        
        if not db_success:
            return jsonify({"erro": "Erro ao finalizar chamado no banco"}), 500

        def update_external_systems():
            try:
                excel_result = update_excel_optimized(id, 'Concluído')
                redmine_result = update_redmine_optimized(id, 5)
                logging.info(f"Chamado {id} finalizado - Excel: {excel_result}, Redmine: {redmine_result}")
            except Exception as e:
                logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

        executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"Chamado {id} finalizado com sucesso",
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }
        
        logging.info(f"✅ Chamado {id} finalizado com sucesso")
        return jsonify(response_data), 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"Erro crítico ao finalizar chamado {id} (tempo: {tempo_erro:.2f}s): {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ============= ROTAS DE OBSERVAÇÕES PARA CHAMADOS =============

@app.route("/chamados/<int:id>/observacoes", methods=["GET", "OPTIONS"])
@cross_origin(origin="http://localhost:5173", methods=["GET", "OPTIONS"], supports_credentials=True)
def obter_observacoes(id):
    """Obtém todas as observações de um chamado"""
    if request.method == "OPTIONS":
        return '', 200

    try:
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado"}), 404

        observacoes_raw = obter_observacoes_chamado(id)
        
        observacoes_lista = []
        if observacoes_raw:
            observacoes_split = observacoes_raw.split('\n\n')
            
            for obs in observacoes_split:
                obs = obs.strip()
                if obs:
                    match = re.match(r'\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2}) - ([^\]]+)\]: (.+)', obs, re.DOTALL)
                    if match:
                        data_str, usuario, conteudo = match.groups()
                        observacoes_lista.append({
                            'data': data_str,
                            'usuario': usuario,
                            'observacao': conteudo.strip(),
                            'timestamp': datetime.strptime(data_str, "%d/%m/%Y %H:%M").isoformat()
                        })
                    else:
                        observacoes_lista.append({
                            'data': 'Data não disponível',
                            'usuario': 'Sistema',
                            'observacao': obs,
                            'timestamp': datetime.now().isoformat()
                        })

        return jsonify({
            "success": True,
            "observacoes": observacoes_lista,
            "total": len(observacoes_lista)
        })

    except Exception as e:
        logging.error(f"Erro ao obter observações: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/chamados/<int:id>/observacao", methods=["PUT", "OPTIONS"])
@cross_origin(origin="http://localhost:5173", methods=["PUT", "OPTIONS"], supports_credentials=True)
def adicionar_observacao(id):
    """Adiciona uma nova observação ao chamado"""
    if request.method == "OPTIONS":
        return '', 200

    try:
        dados = request.get_json()
        nova_obs = dados.get("observacao", "")
        usuario = dados.get("usuario", "Sistema")
        
        if isinstance(nova_obs, str):
            nova_obs = nova_obs.strip()
        else:
            nova_obs = str(nova_obs).strip() if nova_obs else ""
            
        if isinstance(usuario, str):
            usuario = usuario.strip()
        else:
            usuario = str(usuario).strip() if usuario else "Sistema"
        
        if not nova_obs:
            return jsonify({"erro": "Observação não pode estar vazia"}), 400

        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado ou já finalizado"}), 404

        observacoes_existentes = obter_observacoes_chamado(id)
        
        nova_observacao_formatada = formatar_observacao(usuario, nova_obs)
        
        if observacoes_existentes:
            observacoes_atualizadas = f"{observacoes_existentes}\n\n{nova_observacao_formatada}"
        else:
            observacoes_atualizadas = nova_observacao_formatada

        if not update_database_optimized(id, 'update_observacoes', observacoes=observacoes_atualizadas):
            return jsonify({"erro": "Erro ao salvar observação no banco"}), 500

        def update_redmine_background():
            return update_redmine_optimized(id, notes=f"[{usuario}] {nova_obs}")
        
        executor.submit(update_redmine_background)

        return jsonify({
            "success": True,
            "mensagem": "Observação adicionada com sucesso",
            "observacao": {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario": usuario,
                "observacao": nova_obs,
                "timestamp": datetime.now().isoformat()
            }
        }), 201

    except Exception as e:
        logging.error(f"Erro ao adicionar observação: {e}")
        return jsonify({"erro": str(e)}), 500

# ============= ENDPOINTS DE SAÚDE E STATUS =============

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para monitoramento da saúde da aplicação"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Teste para chamados
        cursor.execute("SELECT COUNT(*) FROM dbo.[GRC-Chamados]")
        count_chamados = cursor.fetchone()[0]
        
        # Teste para SARs
        cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar]")
        count_sars = cursor.fetchone()[0]
        
        cursor.close()
        return_connection(conn)
        
        return jsonify({
            "status": "healthy",
            "pool_available_connections": connection_pool.qsize(),
            "pool_max_size": connection_pool.maxsize,
            "total_chamados_no_banco": count_chamados,
            "total_sars_no_banco": count_sars,
            "excel_cache_age_seconds": round(time.time() - excel_cache_time, 2),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/status", methods=["GET"])
def status():
    """Status simples para compatibilidade"""
    return jsonify({
        "status": "OK",
        "pool_connections": connection_pool.qsize(),
        "excel_cache_age": time.time() - excel_cache_time
    })

# ============= INICIALIZAÇÃO DA APLICAÇÃO =============
# ============= INICIALIZAÇÃO DA APLICAÇÃO =============

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console
            logging.FileHandler('chamados_api.log')  # Arquivo de log
        ]
    )
    
    # Inicializar pool de conexões
    logging.info("🚀 Inicializando pool de conexões do banco de dados...")
    init_connection_pool()
    logging.info("✅ Pool de conexões inicializado.")

    # Pré-carregar cache do Excel
    logging.info("📊 Pré-carregando cache do Excel...")
    get_cached_excel_data()
    logging.info("✅ Cache do Excel pré-carregado.")
    
    logging.info("🌐 Iniciando servidor Flask na porta 5007...")
    logging.info("📋 Endpoints disponíveis:")
    logging.info("   === CHAMADOS ===")
    logging.info("   GET  /api/chamados - Lista todos os chamados")
    logging.info("   PUT  /api/chamados/:id - Atualiza chamado")
    logging.info("   PUT  /chamados/:id/assumir - Assumir chamado")
    logging.info("   PUT  /chamados/:id/liberar - Liberar chamado")
    logging.info("   PUT  /chamados/:id/finalizar - Finalizar chamado")
    logging.info("   GET  /chamados/:id/observacoes - Buscar observações")
    logging.info("   PUT  /chamados/:id/observacao - Adicionar observação")
    logging.info("   === SARs ===")
    logging.info("   GET  /api/sars - Lista todos os SARs")
    logging.info("   PUT  /api/sars/:id - Atualiza SAR")
    logging.info("   PUT  /sars/:id/assumir - Assumir SAR")
    logging.info("   PUT  /sars/:id/liberar - Liberar SAR")
    logging.info("   PUT  /sars/:id/finalizar - Finalizar SAR")
    logging.info("   GET  /sars/:id/observacoes - Buscar observações SAR")
    logging.info("   PUT  /sars/:id/observacao - Adicionar observação SAR")
    logging.info("   === SISTEMA ===")
    logging.info("   GET  /health - Status da aplicação")
    
    app.run(debug=True, port=5007, threaded=True)  # ✅ ALTERADO: porta 5007