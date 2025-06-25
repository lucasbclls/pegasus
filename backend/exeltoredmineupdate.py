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

def update_redmine_optimized(chamado_id, status_id=None, notes=None, assignee_id=None):
    """Redmine otimizado com retry e timeout"""
    max_retries = 2
    timeout = 15
    
    for attempt in range(max_retries):
        try:
            url = f"{REDMINE_URL}/{chamado_id}.json"
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
                logging.warning(f"Chamado {chamado_id} não encontrado no Redmine (código 404).")
                return True
            else:
                logging.warning(f"Redmine retornou {response.status_code} para chamado {chamado_id}, tentativa {attempt + 1}. Resposta: {response.text}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout ao atualizar Redmine para chamado {chamado_id} (tentativa {attempt + 1}).")
            if attempt == max_retries - 1:
                return False
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erro inesperado ao atualizar Redmine para chamado {chamado_id} (tentativa {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(1)
    
    return False

def update_database_optimized(chamado_id, operation_type, observacoes=None, campos_atualizacao=None):
    """Operação de banco otimizada com prepared statement e suporte a observações/atualização genérica"""
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
            # ✅ CORREÇÃO: Filtrar campos None para evitar problemas
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

# ============= ROTAS PRINCIPAIS (NOVAS) =============

@app.route("/api/chamados", methods=["GET", "OPTIONS"])
@cross_origin(methods=["GET", "OPTIONS"], supports_credentials=True)
def listar_chamados():
    """✅ NOVA ROTA: Lista todos os chamados para o frontend pai"""
    if request.method == "OPTIONS":
        return '', 200
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # ✅ PRIMEIRO: Descobrir quais colunas existem na tabela
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'GRC-Chamados' 
            ORDER BY ORDINAL_POSITION
        """)
        
        colunas_existentes = [row[0] for row in cursor.fetchall()]
        logging.info(f"📋 Colunas encontradas na tabela: {colunas_existentes}")
        
        # ✅ SEGUNDO: Fazer query com todas as colunas (usando SELECT *)
        cursor.execute("SELECT * FROM dbo.[GRC-Chamados] ORDER BY ID DESC")
        resultados = cursor.fetchall()
        
        # ✅ TERCEIRO: Mapear os resultados usando os índices das colunas
        chamados = []
        for row in resultados:
            chamado = {}
            
            # Mapear cada coluna pelo índice
            for i, coluna in enumerate(colunas_existentes):
                valor = row[i] if i < len(row) else None
                chamado[coluna] = valor if valor is not None else ''
            
            # ✅ Garantir que as colunas esperadas pelo frontend existam
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
        logging.info(f"📄 Exemplo do primeiro chamado: {chamados[0] if chamados else 'Nenhum chamado encontrado'}")
        
        return jsonify(chamados), 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar chamados: {e}")
        return jsonify({"erro": str(e)}), 500
    finally:
        if conn:
            return_connection(conn)

@app.route("/api/chamados/<int:id>", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def atualizar_chamado_api(id):
    """✅ NOVA ROTA: Endpoint /api/chamados/:id para compatibilidade com o frontend pai"""
    if request.method == "OPTIONS":
        return '', 200
    
    dados = request.get_json()
    logging.info(f"✅ Atualizando chamado {id} via API com dados: {dados}")
    
    try:
        # Usando a função de atualização otimizada do banco
        success = update_database_optimized(id, 'generic_update', campos_atualizacao=dados)
        
        if success:
            # ✅ Atualizar Excel/Redmine em background se status foi alterado
            if 'status' in dados:
                novo_status = dados['status']
                responsavel = dados.get('responsavel')
                
                # Atualizar Excel e Redmine em background
                def update_secondary_systems():
                    try:
                        # Mapear status para IDs do Redmine
                        status_map = {
                            'Pendente': 1,
                            'Em Andamento': 2, 
                            'Concluído': 5,
                            'Cancelado': 6
                        }
                        
                        excel_future = executor.submit(update_excel_optimized, id, novo_status, responsavel)
                        redmine_future = executor.submit(update_redmine_optimized, id, status_map.get(novo_status, 1))
                        
                        # Log dos resultados
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

# ============= ROTAS DE ATUALIZAÇÃO DE CHAMADOS =============

@app.route("/chamados/<int:id>", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def atualizar_chamado_direto(id):
    """✅ CORRIGIDO: Endpoint direto /chamados/:id (sem /api/) - sem duplicação"""
    if request.method == "OPTIONS":
        return '', 200
        
    dados = request.get_json()
    logging.info(f"✅ Atualizando chamado {id} diretamente com dados: {dados}")
    
    try:
        success = update_database_optimized(id, 'generic_update', campos_atualizacao=dados)
        
        if success:
            return jsonify({
                "success": True,
                "mensagem": f"Chamado {id} atualizado com sucesso"
            }), 200
        else:
            return jsonify({"erro": "Falha ao atualizar chamado no banco de dados"}), 500
    except Exception as e:
        logging.error(f"Erro ao atualizar chamado: {e}")
        return jsonify({"erro": str(e)}), 500

# ============= ROTAS DE RESPONSÁVEL =============

@app.route("/chamados/<int:id>/assumir", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def assumir_chamado_endpoint(id):
    """✅ CORRIGIDO: Assumir chamado com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200

    data = request.get_json() or {}
    responsavel = data.get("responsavel")
    apenas_visual = data.get("apenas_visual", False)

    if not responsavel:
        return jsonify({"erro": "Responsável não fornecido."}), 400

    try:
        # 1. Validação: Verifica se o chamado existe
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado."}), 404
        
        # 2. Verifica se o chamado já tem responsável
        responsavel_atual = update_database_optimized(id, 'get_responsavel')
        
        if responsavel_atual and responsavel_atual.strip():
            # Chamado já foi assumido por outro usuário
            if responsavel_atual.strip() != responsavel.strip():
                return jsonify({
                    "erro": f"Chamado já foi assumido por {responsavel_atual}",
                    "responsavel_atual": responsavel_atual,
                    "conflito": True
                }), 409
            else:
                # Mesmo usuário tentando assumir novamente
                return jsonify({
                    "success": True,
                    "mensagem": f"Chamado já estava assumido por {responsavel}",
                    "responsavel_atual": responsavel,
                    "responsavel_nome": responsavel,
                    "ja_assumido": True,
                    "apenas_visual": apenas_visual
                }), 200
            
        # 3. Atualização no banco de dados
        db_success = update_database_optimized(id, 'generic_update', campos_atualizacao={'Responsavel': responsavel})
        
        if not db_success:
            return jsonify({"erro": "Erro ao assumir o chamado no banco."}), 500

        # 4. Atualizações assíncronas APENAS se não for apenas visual
        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(id, None, responsavel)
                    redmine_result = update_redmine_optimized(id, assignee_id=1)
                    logging.info(f"Chamado {id} assumido - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

            executor.submit(update_external_systems)

        # 5. Resposta rápida ao frontend
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
    """✅ CORRIGIDO: Liberar chamado com validação melhorada"""
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        data = request.get_json() or {}
        apenas_visual = data.get("apenas_visual", False)
        
        # 1. Validação: Verifica se o chamado existe
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado."}), 404

        # 2. Atualização no banco de dados (responsável para NULL)
        db_success = update_database_optimized(id, 'generic_update', campos_atualizacao={'Responsavel': None})
        
        if not db_success:
            return jsonify({"erro": "Erro ao liberar o chamado no banco."}), 500

        # 3. Atualizações assíncronas APENAS se não for apenas visual
        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(id, None, None)
                    redmine_result = update_redmine_optimized(id, assignee_id=None)
                    logging.info(f"Chamado {id} liberado - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

            executor.submit(update_external_systems)

        # 4. Resposta rápida ao frontend
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

# ============= ROTAS DE FINALIZAÇÃO E CANCELAMENTO =============

# ============= ROTAS DE FINALIZAÇÃO E CANCELAMENTO =============

@app.route("/chamados/<int:id>/finalizar", methods=["PUT", "OPTIONS"])
@cross_origin(methods=["PUT", "OPTIONS"], supports_credentials=True)
def finalizar_chamado(id):
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado"}), 404

        # Finalizar o chamado no banco de dados
        db_success = update_database_optimized(id, 'delete')
        
        if not db_success:
            return jsonify({"erro": "Erro ao finalizar chamado no banco"}), 500

        # Operações secundárias em background
        def update_external_systems():
            try:
                excel_result = update_excel_optimized(id, 'Concluido')
                # Finalizar no Redmine com status 5 (concluído)
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





def cancelar_chamado(id):
    if request.method == "OPTIONS":
        return '', 200
        
    start_time = time.time()
    
    try:
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado"}), 404

        db_success = update_database_optimized(id, 'delete')
        
        if not db_success:
            return jsonify({"erro": "Erro ao cancelar chamado no banco"}), 500

        # Operações secundárias em background
        def update_external_systems():
            try:
                excel_result = update_excel_optimized(id, 'Cancelado')
                redmine_result = update_redmine_optimized(id, 6)
                logging.info(f"Chamado {id} cancelado - Excel: {excel_result}, Redmine: {redmine_result}")
            except Exception as e:
                logging.error(f"Erro ao atualizar sistemas externos para chamado {id}: {e}")

        executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"Chamado {id} cancelado com sucesso",
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }
        
        logging.info(f"✅ Chamado {id} cancelado com sucesso")
        return jsonify(response_data), 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"Erro ao cancelar chamado {id} (tempo: {tempo_erro:.2f}s): {e}")
        return jsonify({"erro": "Erro interno do servidor"}), 500






# ============= ROTAS DE OBSERVAÇÕES =============

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
        
        # Verificar se são strings antes de fazer strip()
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

        # Verificar se o chamado existe e está ativo
        if not verificar_status_chamado(id):
            return jsonify({"erro": "Chamado não encontrado ou já finalizado"}), 404

        # Obter observações existentes
        observacoes_existentes = obter_observacoes_chamado(id)
        
        # Formatar nova observação
        nova_observacao_formatada = formatar_observacao(usuario, nova_obs)
        
        # Concatenar com observações existentes
        if observacoes_existentes:
            observacoes_atualizadas = f"{observacoes_existentes}\n\n{nova_observacao_formatada}"
        else:
            observacoes_atualizadas = nova_observacao_formatada

        # Salvar no banco de dados
        if not update_database_optimized(id, 'update_observacoes', observacoes=observacoes_atualizadas):
            return jsonify({"erro": "Erro ao salvar observação no banco"}), 500

        # Atualizar no Redmine de forma assíncrona
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
        cursor.execute("SELECT COUNT(*) FROM dbo.[GRC-Chamados]")
        count = cursor.fetchone()[0]
        cursor.close()
        return_connection(conn)
        
        return jsonify({
            "status": "healthy",
            "pool_available_connections": connection_pool.qsize(),
            "pool_max_size": connection_pool.maxsize,
            "total_chamados_no_banco": count,
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
    
    logging.info("🌐 Iniciando servidor Flask na porta 5000...")
    logging.info("📋 Endpoints disponíveis:")
    logging.info("   GET  /api/chamados - Lista todos os chamados")
    logging.info("   PUT  /api/chamados/:id - Atualiza chamado (API)")
    logging.info("   PUT  /chamados/:id - Atualiza chamado (direto)")
    logging.info("   PUT  /chamados/:id/assumir - Assumir chamado")
    logging.info("   PUT  /chamados/:id/liberar - Liberar chamado")
    logging.info("   PUT  /chamados/:id/finalizar - Finalizar chamado")
    logging.info("   PUT  /chamados/:id/cancelar - Cancelar chamado")
    logging.info("   GET  /chamados/:id/observacoes - Buscar observações")
    logging.info("   PUT  /chamados/:id/observacao - Adicionar observação")
    logging.info("   GET  /health - Status da aplicação")
    
    app.run(debug=True, port=5000, threaded=True)