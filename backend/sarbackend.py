from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import pyodbc
import pandas as pd
import requests
from datetime import datetime
import re
import logging
from threading import Thread
import time
from functools import lru_cache
import asyncio
import json
from queue import Queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# ============= CONFIGURAÇÕES =============

# URLs e chaves da API
REDMINE_URL_BASE = "http://187.36.193.239/redmine"
REDMINE_URL = "http://187.36.193.239/redmine/issues"
REDMINE_API_KEY = "df3745b4f0356e84781e4254d109efd3e31e0eb6"

# ✅ ADICIONAR: Configuração do Excel (ADAPTE O CAMINHO)
EXCEL_PATH = r'C:\Users\Paulo Lucas\OneDrive - Claro SA\USER-DTC_HE_INFRA - ES - Documentos\ExecucaoSar_ES.xlsx'
ABA_EXCEL = 'ExecucaoSar'  # Nome da aba na planilha

# Headers para Redmine
HEADERS = {"Content-Type": "application/json", "X-Redmine-API-Key": REDMINE_API_KEY}

# CORS configurado
CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"], 
     supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# ============= POOLS E CACHES =============

# Pool de conexões para o banco
connection_pool = Queue(maxsize=10)
connection_lock = threading.Lock()

# ✅ ADICIONAR: Pool de threads para operações assíncronas
executor = ThreadPoolExecutor(max_workers=10)

# ✅ ADICIONAR: Pool de conexões para requests
session = requests.Session()
session.headers.update(HEADERS)

# ✅ ADICIONAR: Cache para Excel
excel_cache = {}
excel_cache_time = 0
CACHE_DURATION = 60

# ============= FUNÇÕES DE CONEXÃO (mantidas do original) =============

def init_connection_pool():
    """Pool otimizado com retry e validação"""
    global connection_pool
    
    # Limpar pool existente se houver
    while not connection_pool.empty():
        try:
            old_conn = connection_pool.get_nowait()
            old_conn.close()
        except:
            pass
    
    conexoes_criadas = 0
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
            conexoes_criadas += 1
            logging.info(f"✅ Conexão ExecucaoSar {i+1} criada e testada com sucesso")
        except Exception as e:
            logging.error(f"❌ Erro ao criar conexão ExecucaoSar {i+1}: {e}")
            continue
    
    if conexoes_criadas == 0:
        logging.critical("❌ ERRO CRÍTICO: Nenhuma conexão foi criada no pool!")
        logging.warning("⚠️ Continuando sem pool, usando conexões individuais")
    
    logging.info(f"✅ Pool inicializado com {conexoes_criadas}/10 conexões")

def create_new_connection():
    """Cria nova conexão quando o pool está vazio"""
    try:
        return pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=localhost;'
            'DATABASE=powerbi;'
            'Trusted_Connection=yes;'
            'Connection Timeout=30;'
            'Command Timeout=30;'
        )
    except Exception as e:
        logging.error(f"❌ Erro ao criar nova conexão: {e}")
        raise

def get_connection():
    """Obtém conexão com timeout e retry"""
    try:
        if not connection_pool.empty():
            conn = connection_pool.get(timeout=2)
            
            # Validar conexão
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
                except:
                    pass
        
        return create_new_connection()
            
    except Exception as e:
        logging.warning(f"Erro ao obter conexão do pool, criando nova: {e}")
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
        except:
            pass

# ============= ✅ NOVAS FUNÇÕES: INTEGRAÇÃO COM EXCEL =============

@lru_cache(maxsize=100)
def get_cached_excel_data():
    """Cache dos dados do Excel com TTL"""
    global excel_cache, excel_cache_time
    current_time = time.time()
    
    if current_time - excel_cache_time > CACHE_DURATION:
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=ABA_EXCEL)
            df.columns = [re.sub(r'[:\s]+$', '', col.strip().lower()) for col in df.columns]
            excel_cache = df.to_dict('records')
            excel_cache_time = current_time
            logging.info(f"✅ Cache do Excel atualizado: {len(excel_cache)} registros")
        except Exception as e:
            logging.error(f"❌ Erro ao ler Excel: {e}")
            return None
    
    return excel_cache

def update_excel_optimized(num_sar, novo_status, responsavel=None):
    """✅ NOVA: Atualização otimizada do Excel com cache inteligente"""
    try:
        # Ler Excel
        df = pd.read_excel(EXCEL_PATH, sheet_name=ABA_EXCEL)
        df.columns = [re.sub(r'[:\s]+$', '', col.strip().lower()) for col in df.columns]
        
        # Verificar se coluna NumSar existe (pode ter nomes diferentes)
        coluna_numsar = None
        for col in df.columns:
            if 'numsar' in col or 'numero' in col or 'sar' in col:
                coluna_numsar = col
                break
        
        if not coluna_numsar:
            logging.error("❌ Coluna NumSar não encontrada no Excel.")
            return False

        # Buscar registro do SAR
        mask = df[coluna_numsar] == num_sar
        if not mask.any():
            logging.warning(f"⚠️ SAR {num_sar} não encontrado no Excel para atualização.")
            return False
            
        # Atualizar status se fornecido
        if novo_status:
            status_cols = [col for col in df.columns if 'status' in col]
            if status_cols:
                df.loc[mask, status_cols[0]] = novo_status
                logging.info(f"✅ Status do SAR {num_sar} atualizado para: {novo_status}")
        
        # Atualizar responsável se fornecido
        if responsavel is not None:
            resp_cols = [col for col in df.columns if 'responsavel' in col or 'responsável' in col]
            if resp_cols:
                df.loc[mask, resp_cols[0]] = responsavel
                logging.info(f"✅ Responsável do SAR {num_sar} atualizado para: {responsavel}")
        
        # Gravar Excel com proteção OneDrive
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=ABA_EXCEL, index=False)
        
        # Limpar cache
        global excel_cache_time
        excel_cache_time = 0
        get_cached_excel_data.cache_clear()
        
        logging.info(f"✅ Excel atualizado com sucesso para SAR {num_sar}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao atualizar Excel para SAR {num_sar}: {e}")
        return False

# ============= ✅ NOVAS FUNÇÕES: INTEGRAÇÃO COM REDMINE OTIMIZADA =============

def update_redmine_optimized(num_sar, status_id=None, notes=None, assignee_id=None):
    """✅ CORRIGIDA: Redmine otimizado com retry e timeout usando coluna ID_redmine"""
    
    # Primeiro, buscar ID do Redmine da coluna ID_redmine
    id_redmine = buscar_id_redmine_por_numsar(num_sar)
    
    if not id_redmine:
        logging.warning(f"⚠️ ID Redmine não encontrado para SAR {num_sar} na coluna ID_redmine")
        logging.info(f"📝 SAR {num_sar} pode não ter sido criado no Redmine ainda ou coluna ID_redmine está vazia")
        return True  # Não é erro crítico, pode ser que o SAR não tenha Redmine
    
    logging.info(f"🔍 Iniciando atualização Redmine para SAR {num_sar} → ID Redmine: #{id_redmine}")
    
    max_retries = 3
    timeout = 20
    
    for attempt in range(max_retries):
        try:
            url = f"{REDMINE_URL}/{id_redmine}.json"
            payload = {"issue": {}}
            
            # Montar payload com os dados fornecidos
            if status_id:
                payload["issue"]["status_id"] = status_id
                logging.info(f"📝 Atualizando status do Redmine #{id_redmine} para status_id: {status_id}")
            
            if notes:
                timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                payload["issue"]["notes"] = f"**[{timestamp}] - Sistema ExecucaoSar**\n\n{notes}"
                logging.info(f"📝 Adicionando nota ao Redmine #{id_redmine}: {notes[:50]}...")
            
            if assignee_id is not None:
                payload["issue"]["assigned_to_id"] = assignee_id
                logging.info(f"📝 Atualizando responsável do Redmine #{id_redmine} para ID: {assignee_id}")
            
            logging.info(f"🌐 Tentativa {attempt + 1}/{max_retries} - Enviando para: {url}")
            logging.info(f"📦 Payload: {json.dumps(payload, indent=2)}")
            
            response = session.put(url, json=payload, timeout=timeout)
            
            logging.info(f"📡 Resposta Redmine: {response.status_code}")
            
            if response.status_code == 200:
                logging.info(f"✅ Redmine atualizado com SUCESSO para SAR {num_sar} (ID: #{id_redmine})")
                return True
                
            elif response.status_code == 404:
                logging.warning(f"⚠️ Chamado #{id_redmine} não encontrado no Redmine (404)")
                logging.warning(f"⚠️ Verifique se o ID {id_redmine} realmente existe no Redmine")
                return False  # 404 é erro real
                
            elif response.status_code == 422:
                logging.error(f"❌ Dados inválidos enviados para Redmine #{id_redmine} (422)")
                logging.error(f"❌ Resposta: {response.text}")
                return False  # Erro de validação
                
            else:
                error_text = response.text[:200] if response.text else "Sem resposta"
                logging.warning(f"⚠️ Redmine retornou {response.status_code} para SAR {num_sar} (tentativa {attempt + 1})")
                logging.warning(f"⚠️ Resposta: {error_text}")
                
                if attempt == max_retries - 1:
                    logging.error(f"❌ Todas as tentativas falharam para SAR {num_sar}")
                    return False
                    
                time.sleep(2)  # Aumentado o tempo de espera
                
        except requests.exceptions.Timeout:
            logging.warning(f"⏰ Timeout ao atualizar Redmine para SAR {num_sar} (tentativa {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                logging.error(f"❌ Timeout final para SAR {num_sar}")
                return False
            time.sleep(2)
            
        except requests.exceptions.ConnectionError as e:
            logging.error(f"🌐 Erro de conexão com Redmine para SAR {num_sar}: {e}")
            if attempt == max_retries - 1:
                logging.error(f"❌ Erro de conexão final para SAR {num_sar}")
                return False
            time.sleep(3)
            
        except Exception as e:
            logging.error(f"❌ Erro inesperado ao atualizar Redmine SAR {num_sar} (tentativa {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logging.error(f"❌ Erro final para SAR {num_sar}: {e}")
                return False
            time.sleep(2)
    
    return False

# ============= FUNÇÕES AUXILIARES (mantidas e melhoradas) =============

def converter_data(data):
    """Converte data para formato ISO"""
    if isinstance(data, datetime):
        return data.isoformat()
    return data

def verificar_status_sar(num_sar):
    """Verifica se o ExecucaoSar existe"""
    return update_database_optimized(num_sar, 'check_status')

def buscar_id_redmine_por_numsar(num_sar):
    """✅ MELHORADA: Busca ID do Redmine pela coluna ID_redmine com logs detalhados"""
    conn = None
    try:
        logging.info(f"🔍 Buscando ID Redmine para SAR {num_sar} na coluna ID_redmine...")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query para buscar o ID_redmine
        cursor.execute("SELECT ID_redmine FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (num_sar,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            id_redmine = result[0]
            if id_redmine and str(id_redmine).strip():
                # Converter para int se for string numérica
                try:
                    id_redmine_int = int(id_redmine)
                    logging.info(f"✅ ID Redmine encontrado para SAR {num_sar}: #{id_redmine_int}")
                    return id_redmine_int
                except (ValueError, TypeError):
                    logging.warning(f"⚠️ ID Redmine inválido para SAR {num_sar}: '{id_redmine}' (não é número)")
                    return None
            else:
                logging.warning(f"⚠️ ID Redmine está vazio/null para SAR {num_sar}")
                return None
        else:
            logging.warning(f"⚠️ SAR {num_sar} não encontrado na tabela ExecucaoSar")
            return None
            
    except Exception as e:
        logging.error(f"❌ Erro ao buscar ID Redmine para SAR {num_sar}: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)

def verificar_coluna_id_redmine():
    """✅ NOVA: Função para verificar se a coluna ID_redmine existe na tabela"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se a coluna ID_redmine existe
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'ExecucaoSar' 
            AND COLUMN_NAME = 'ID_redmine'
        """)
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            logging.info("✅ Coluna ID_redmine encontrada na tabela ExecucaoSar")
            
            # Verificar quantos registros têm ID_redmine preenchido
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar] WHERE ID_redmine IS NOT NULL AND ID_redmine != ''")
            count_preenchidos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar]")
            count_total = cursor.fetchone()[0]
            
            cursor.close()
            
            logging.info(f"📊 Estatísticas ID_redmine: {count_preenchidos}/{count_total} registros com ID preenchido")
            return True
        else:
            logging.error("❌ Coluna ID_redmine NÃO encontrada na tabela ExecucaoSar!")
            logging.error("❌ Você precisa criar esta coluna na tabela para integração com Redmine")
            return False
            
    except Exception as e:
        logging.error(f"❌ Erro ao verificar coluna ID_redmine: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)

# ============= ✅ NOVA: SISTEMA DE OBSERVAÇÕES ROBUSTO =============

def obter_observacoes_sar(num_sar):
    """Obtém as observações do SAR do banco de dados"""
    return update_database_optimized(num_sar, 'get_observacoes')

def salvar_observacoes_sar(num_sar, observacoes):
    """Salva as observações do SAR no banco de dados"""
    return update_database_optimized(num_sar, 'update_observacoes', observacoes=observacoes)

def formatar_observacao(usuario, observacao):
    """Formata uma nova observação com timestamp e usuário"""
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"[{data_hora} - {usuario}]: {observacao}"

# ============= FUNÇÃO DE BANCO MELHORADA =============

def update_database_optimized(num_sar, operation_type, observacoes=None, campos_atualizacao=None, campo_responsavel=None):
    """✅ MELHORADA: Operação de banco otimizada para ExecucaoSar com suporte a observações"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if operation_type == 'delete':
            # ✅ NOVA: Operação de DELETE para finalização
            cursor.execute("DELETE FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (num_sar,))
            
        elif operation_type == 'update_observacoes':
            # ✅ NOVA: Atualização de observações
            cursor.execute(
                "UPDATE dbo.[ExecucaoSar] SET Observacoes = ? WHERE NumSar = ?", 
                (observacoes, num_sar)
            )
            
        elif operation_type == 'get_observacoes':
            # ✅ NOVA: Buscar observações
            cursor.execute("SELECT Observacoes FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (num_sar,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else ""
            
        elif operation_type == 'check_status':
            cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (num_sar,))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
            
        elif operation_type == 'get_responsavel':
            campo = campo_responsavel or 'ResponsavelHub'
            cursor.execute(f"SELECT [{campo}] FROM dbo.[ExecucaoSar] WHERE NumSar = ?", (num_sar,))
            result = cursor.fetchone()
            return result[0] if result else None
            
        elif operation_type == 'generic_update' and campos_atualizacao:
            # Mapear campos do frontend para campos da ExecucaoSar
            mapeamento_campos = {
                'status': 'Status',
                'cidade': 'Cidade',
                'acao': 'Acao',
                'areaTecnica': 'AreaTecnica',
                'designacao': 'Designacao',
                'enderecoNap': 'EnderecoNap',
                'quantPort': 'QuantPort',
                'caminho': 'Caminho',
                'responsavelHub': 'ResponsavelHub',
                'responsavelDTC': 'ResponsavelDTC',
                'dataVenc': 'DataVenc',
                'dataExecucao': 'DataExecucao',
                'dataCancelamento': 'DataCancelamento',
                'idadeExecucao': 'IdadeExecucao',
                'anoMes': 'AnoMes'
            }
            
            # Converter campos para nomes da tabela
            campos_db = {}
            for key, value in campos_atualizacao.items():
                campo_db = mapeamento_campos.get(key, key)
                campos_db[campo_db] = value
            
            # Filtrar campos válidos
            campos_filtrados = {k: v for k, v in campos_db.items() 
                              if v is not None or k in ['ResponsavelHub', 'ResponsavelDTC']}
            
            if campos_filtrados:
                set_clauses = [f"[{k}] = ?" for k in campos_filtrados.keys()]
                values = list(campos_filtrados.values())
                query = f"UPDATE dbo.[ExecucaoSar] SET {', '.join(set_clauses)} WHERE NumSar = ?"
                cursor.execute(query, (*values, num_sar))

        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro na operação de banco para ExecucaoSar {num_sar} (tipo: {operation_type}): {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    finally:
        if conn:
            return_connection(conn)

# ============= ROTAS EXISTENTES (mantidas) =============

@app.route("/", methods=["GET"])
def home():
    """Rota raiz para confirmar que a API está funcionando"""
    return jsonify({
        "message": "API ExecucaoSar está funcionando!",
        "version": "2.0 - Com integração Excel/Redmine",
        "endpoints": [
            "GET /api/sars - Lista todos os SARs",
            "PUT /api/sars/:numsar - Atualiza SAR",
            "PUT /sars/:numsar/assumir - Assumir SAR",
            "PUT /sars/:numsar/liberar - Liberar SAR",
            "PUT /sars/:numsar/finalizar - Finalizar SAR (DELETE + Excel + Redmine)",
            "PUT /sars/:numsar/cancelar - Cancelar SAR (DELETE + Excel + Redmine)",
            "GET /sars/:numsar/observacoes - Buscar observações",
            "PUT /sars/:numsar/observacao - Adicionar observação",
            "GET /health - Status da aplicação"
        ]
    })

@app.route("/test", methods=["GET"])
def test_connection():
    """Teste de conexão com o banco"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar]")
        count = cursor.fetchone()[0]
        cursor.close()
        return_connection(conn)
        
        return jsonify({
            "status": "success",
            "message": "Conexão com banco OK",
            "total_records": count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro na conexão: {str(e)}"
        }), 500

@app.route("/api/sars", methods=["GET", "OPTIONS"])
def listar_sars():
    """Lista todos os registros da ExecucaoSar para o frontend"""
    
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                NumSar,
                DataSolicitacao,
                Cidade,
                Acao,
                AreaTecnica,
                Designacao,
                EnderecoNap,
                QuantPort,
                Caminho,
                Status,
                ResponsavelHub,
                DataVenc,
                DataExecucao,
                DataCancelamento,
                IdadeExecucao,
                AnoMes,
                ResponsavelDTC
            FROM dbo.[ExecucaoSar] 
            ORDER BY DataSolicitacao DESC
        """)
        
        resultados = cursor.fetchall()
        
        # Mapear os resultados para formato esperado pelo frontend
        sars = []
        for row in resultados:
            sar_data = {
                # Campos principais
                'id': str(row[0]) if row[0] else '',
                'numeroSar': str(row[0]) if row[0] else '',
                'NumSar': str(row[0]) if row[0] else '',
                
                # Dados da ExecucaoSar
                'dataSolicitacao': converter_data(row[1]),
                'cidade': str(row[2]) if row[2] else '',
                'acao': str(row[3]) if row[3] else '',
                'areaTecnica': str(row[4]) if row[4] else '',
                'designacao': str(row[5]) if row[5] else '',
                'enderecoNap': str(row[6]) if row[6] else '',
                'quantPort': int(row[7]) if row[7] else 0,
                'caminho': str(row[8]) if row[8] else '',
                'status': str(row[9]) if row[9] else 'Pendente',
                'responsavelHub': str(row[10]) if row[10] else '',
                'dataVenc': converter_data(row[11]),
                'dataExecucao': converter_data(row[12]),
                'dataCancelamento': converter_data(row[13]),
                'idadeExecucao': int(row[14]) if row[14] else 0,
                'anoMes': converter_data(row[15]),
                'responsavelDTC': str(row[16]) if row[16] else '',
                
                # Campos para compatibilidade com frontend
                'titulo': f"{row[3] or 'Serviço'} - {row[4] or 'Técnico'}",
                'tipoServico': str(row[3]) if row[3] else '',
                'tecnologia': str(row[4]) if row[4] else '',
                'endereco': str(row[6]) if row[6] else '',
                'equipamento': f"{row[7] or 0} portas" if row[7] else '',
                'descricaoServico': str(row[8]) if row[8] else '',
                'dataAgendamento': converter_data(row[1]),
                'horaConclusao': converter_data(row[12]),
                'responsavel': str(row[10] or row[16] or ''),
                'prioridade': 'Normal',
                'cliente': '',
                'bairro': '',
                'tempoEstimado': '',
                'horaInicio': '',
                'observacoes': ''
            }
            
            sars.append(sar_data)
        
        cursor.close()
        
        logging.info(f"✅ Listando {len(sars)} registros da ExecucaoSar")
        
        response = jsonify(sars)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Content-Type', 'application/json')
        
        return response, 200
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar ExecucaoSar: {e}")
        error_response = jsonify({"erro": str(e), "detalhes": "Erro ao buscar dados da ExecucaoSar"})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500
    finally:
        if conn:
            return_connection(conn)

# ============= ✅ ROTAS MELHORADAS: ASSUMIR/LIBERAR =============

@app.route("/sars/<string:num_sar>/assumir", methods=["PUT", "OPTIONS"])
def assumir_execucaosar(num_sar):
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "PUT,OPTIONS")
        return response, 200

    try:
        dados = request.get_json(silent=True) or {}
        novo_responsavel = dados.get("responsavel")
        apenas_visual = dados.get("apenas_visual", False)

        if not novo_responsavel:
            return jsonify({"erro": "Responsável não fornecido"}), 400

        # Verificar se SAR existe
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado"}), 404

        # Verificar se já tem responsável
        responsavel_atual = update_database_optimized(num_sar, 'get_responsavel')
        
        if responsavel_atual and responsavel_atual.strip():
            if responsavel_atual.strip() != novo_responsavel.strip():
                return jsonify({
                    "erro": f"SAR já foi assumido por {responsavel_atual}",
                    "responsavel_atual": responsavel_atual,
                    "conflito": True
                }), 409

        # Atualizar banco
        success = update_database_optimized(
            num_sar,
            "generic_update",
            campos_atualizacao={
                "responsavelHub": novo_responsavel,
                "status": "Em Andamento"
            }
        )

        if not success:
            return jsonify({"erro": "Erro ao assumir o SAR no banco"}), 500

        # ✅ NOVA: Atualizações assíncronas APENAS se não for apenas visual
        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(num_sar, "Em Andamento", novo_responsavel)
                    redmine_result = update_redmine_optimized(num_sar, status_id=2, assignee_id=1)
                    logging.info(f"SAR {num_sar} assumido - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para SAR {num_sar}: {e}")

            executor.submit(update_external_systems)

        response = jsonify({
            "success": True,
            "mensagem": f"SAR {num_sar} assumido com sucesso por {novo_responsavel}",
            "responsavel_atual": novo_responsavel,
            "apenas_visual": apenas_visual
        })

        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200

    except Exception as e:
        logging.error(f"❌ Erro ao assumir SAR {num_sar}: {e}")
        error_response = jsonify({"erro": str(e)})
        error_response.headers.add("Access-Control-Allow-Origin", "*")
        return error_response, 500

@app.route("/sars/<string:num_sar>/liberar", methods=["PUT", "OPTIONS"])
def liberar_execucaosar(num_sar):
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "PUT,OPTIONS")
        return response, 200

    try:
        dados = request.get_json() or {}
        apenas_visual = dados.get("apenas_visual", False)
        
        # Verificar se SAR existe
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado"}), 404

        # Atualizar banco
        success = update_database_optimized(
            num_sar,
            "generic_update",
            campos_atualizacao={
                "responsavelHub": None,
                "responsavelDTC": None,
                "status": "Pendente"
            }
        )

        if not success:
            return jsonify({"erro": "Erro ao liberar o SAR no banco"}), 500

        # ✅ NOVA: Atualizações assíncronas APENAS se não for apenas visual
        if not apenas_visual:
            def update_external_systems():
                try:
                    excel_result = update_excel_optimized(num_sar, "Pendente", None)
                    redmine_result = update_redmine_optimized(num_sar, status_id=1, assignee_id=None)
                    logging.info(f"SAR {num_sar} liberado - Excel: {excel_result}, Redmine: {redmine_result}")
                except Exception as e:
                    logging.error(f"Erro ao atualizar sistemas externos para SAR {num_sar}: {e}")

            executor.submit(update_external_systems)

        response = jsonify({
            "success": True,
            "mensagem": f"SAR {num_sar} liberado com sucesso",
            "responsavel_atual": None,
            "apenas_visual": apenas_visual
        })

        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200

    except Exception as e:
        logging.error(f"❌ Erro ao liberar SAR {num_sar}: {e}")
        error_response = jsonify({"erro": str(e)})
        error_response.headers.add("Access-Control-Allow-Origin", "*")
        return error_response, 500

# ============= ✅ NOVAS ROTAS: FINALIZAR E CANCELAR =============

@app.route("/sars/<string:num_sar>/finalizar", methods=["PUT", "OPTIONS"])
def finalizar_execucaosar(num_sar):
    """✅ NOVA: Finalizar SAR com DELETE + Excel + Redmine"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "PUT,OPTIONS")
        return response, 200

    start_time = time.time()
    
    try:
        # Verificar se SAR existe
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado"}), 404

        # ✅ NOVA: Deletar do banco (igual ao sistema de chamados)
        db_success = update_database_optimized(num_sar, 'delete')
        
        if not db_success:
            return jsonify({"erro": "Erro ao finalizar SAR no banco"}), 500

        # ✅ NOVA: Operações secundárias em background
        def update_external_systems():
            try:
                excel_result = update_excel_optimized(num_sar, 'Concluído')
                # Finalizar no Redmine com status 3 (concluído)
                redmine_result = update_redmine_optimized(num_sar, status_id=3)
                logging.info(f"SAR {num_sar} finalizado - Excel: {excel_result}, Redmine: {redmine_result}")
            except Exception as e:
                logging.error(f"Erro ao atualizar sistemas externos para SAR {num_sar}: {e}")

        executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"SAR {num_sar} finalizado com sucesso",
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }
        
        logging.info(f"✅ SAR {num_sar} finalizado com sucesso")
        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"❌ Erro crítico ao finalizar SAR {num_sar} (tempo: {tempo_erro:.2f}s): {e}")
        error_response = jsonify({"erro": "Erro interno do servidor"})
        error_response.headers.add("Access-Control-Allow-Origin", "*")
        return error_response, 500

@app.route("/sars/<string:num_sar>/cancelar", methods=["PUT", "OPTIONS"])
def cancelar_execucaosar(num_sar):
    """✅ NOVA: Cancelar SAR com DELETE + Excel + Redmine"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "PUT,OPTIONS")
        return response, 200

    start_time = time.time()
    
    try:
        # Verificar se SAR existe
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado"}), 404

        # ✅ NOVA: Deletar do banco
        db_success = update_database_optimized(num_sar, 'delete')
        
        if not db_success:
            return jsonify({"erro": "Erro ao cancelar SAR no banco"}), 500

        # ✅ NOVA: Operações secundárias em background
        def update_external_systems():
            try:
                excel_result = update_excel_optimized(num_sar, 'Cancelado')
                # Cancelar no Redmine com status 5 (cancelado)
                redmine_result = update_redmine_optimized(num_sar, status_id=5)
                logging.info(f"SAR {num_sar} cancelado - Excel: {excel_result}, Redmine: {redmine_result}")
            except Exception as e:
                logging.error(f"Erro ao atualizar sistemas externos para SAR {num_sar}: {e}")

        executor.submit(update_external_systems)

        response_data = {
            "success": True,
            "mensagem": f"SAR {num_sar} cancelado com sucesso",
            "tempo_processamento_resposta": round(time.time() - start_time, 2)
        }
        
        logging.info(f"✅ SAR {num_sar} cancelado com sucesso")
        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200

    except Exception as e:
        tempo_erro = time.time() - start_time
        logging.error(f"❌ Erro ao cancelar SAR {num_sar} (tempo: {tempo_erro:.2f}s): {e}")
        error_response = jsonify({"erro": "Erro interno do servidor"})
        error_response.headers.add("Access-Control-Allow-Origin", "*")
        return error_response, 500

# ============= ✅ NOVAS ROTAS: SISTEMA DE OBSERVAÇÕES =============

@app.route("/sars/<string:num_sar>/observacoes", methods=["GET", "OPTIONS"])
def obter_observacoes(num_sar):
    """✅ NOVA: Obtém todas as observações de um SAR"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response

    try:
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado"}), 404

        observacoes_raw = obter_observacoes_sar(num_sar)
        
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

        response = jsonify({
            "success": True,
            "observacoes": observacoes_lista,
            "total": len(observacoes_lista)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        logging.error(f"❌ Erro ao obter observações: {e}")
        error_response = jsonify({"erro": str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route("/sars/<string:num_sar>/observacao", methods=["PUT", "OPTIONS"])
def adicionar_observacao(num_sar):
    """✅ NOVA: Adiciona uma nova observação ao SAR"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response

    try:
        dados = request.get_json()
        nova_obs = dados.get("observacao", "")
        usuario = dados.get("usuario", "Sistema")
        
        # Verificar se são strings
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

        # Verificar se o SAR existe
        if not verificar_status_sar(num_sar):
            return jsonify({"erro": "SAR não encontrado ou já finalizado"}), 404

        # Obter observações existentes
        observacoes_existentes = obter_observacoes_sar(num_sar)
        
        # Formatar nova observação
        nova_observacao_formatada = formatar_observacao(usuario, nova_obs)
        
        # Concatenar com observações existentes
        if observacoes_existentes:
            observacoes_atualizadas = f"{observacoes_existentes}\n\n{nova_observacao_formatada}"
        else:
            observacoes_atualizadas = nova_observacao_formatada

        # Salvar no banco de dados
        if not update_database_optimized(num_sar, 'update_observacoes', observacoes=observacoes_atualizadas):
            return jsonify({"erro": "Erro ao salvar observação no banco"}), 500

        # ✅ NOVA: Atualizar no Redmine de forma assíncrona
        def update_redmine_background():
            return update_redmine_optimized(num_sar, notes=f"[{usuario}] {nova_obs}")
        
        executor.submit(update_redmine_background)

        response = jsonify({
            "success": True,
            "mensagem": "Observação adicionada com sucesso",
            "observacao": {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario": usuario,
                "observacao": nova_obs,
                "timestamp": datetime.now().isoformat()
            }
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 201

    except Exception as e:
        logging.error(f"❌ Erro ao adicionar observação: {e}")
        error_response = jsonify({"erro": str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

# ============= ✅ NOVA ROTA: TESTE DE INTEGRAÇÃO REDMINE =============

@app.route("/test-redmine/<string:num_sar>", methods=["GET", "OPTIONS"])
def test_redmine_integration(num_sar):
    """✅ NOVA: Teste específico da integração com Redmine"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    try:
        # 1. Verificar se SAR existe
        existe_sar = verificar_status_sar(num_sar)
        
        # 2. Buscar ID do Redmine
        id_redmine = buscar_id_redmine_por_numsar(num_sar)
        
        # 3. Testar conexão com Redmine se ID existir
        redmine_status = None
        redmine_error = None
        
        if id_redmine:
            try:
                url = f"{REDMINE_URL}/{id_redmine}.json"
                response_redmine = session.get(url, timeout=10)
                
                if response_redmine.status_code == 200:
                    redmine_data = response_redmine.json()
                    issue = redmine_data.get('issue', {})
                    redmine_status = {
                        "conectado": True,
                        "status_code": 200,
                        "subject": issue.get('subject', 'N/A'),
                        "status": issue.get('status', {}).get('name', 'N/A'),
                        "assigned_to": issue.get('assigned_to', {}).get('name', 'Não atribuído'),
                        "created_on": issue.get('created_on', 'N/A'),
                        "updated_on": issue.get('updated_on', 'N/A')
                    }
                else:
                    redmine_status = {
                        "conectado": False,
                        "status_code": response_redmine.status_code,
                        "erro": f"HTTP {response_redmine.status_code}: {response_redmine.text[:100]}"
                    }
                    
            except Exception as e:
                redmine_error = str(e)
                redmine_status = {
                    "conectado": False,
                    "erro": f"Erro de conexão: {redmine_error}"
                }
        
        resultado = {
            "num_sar": num_sar,
            "sar_existe_banco": existe_sar,
            "id_redmine_encontrado": id_redmine,
            "redmine_url_teste": f"{REDMINE_URL}/{id_redmine}.json" if id_redmine else None,
            "redmine_status": redmine_status,
            "timestamp": datetime.now().isoformat(),
            "conclusao": {
                "pode_atualizar_redmine": bool(existe_sar and id_redmine and redmine_status and redmine_status.get("conectado")),
                "motivo_falha": None
            }
        }
        
        # Diagnóstico
        if not existe_sar:
            resultado["conclusao"]["motivo_falha"] = f"SAR {num_sar} não existe na tabela ExecucaoSar"
        elif not id_redmine:
            resultado["conclusao"]["motivo_falha"] = f"Coluna ID_redmine está vazia para SAR {num_sar}"
        elif redmine_status and not redmine_status.get("conectado"):
            resultado["conclusao"]["motivo_falha"] = f"Erro ao conectar com Redmine: {redmine_status.get('erro')}"
        
        response = jsonify(resultado)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        logging.error(f"❌ Erro no teste Redmine para SAR {num_sar}: {e}")
        error_response = jsonify({
            "erro": str(e),
            "num_sar": num_sar,
            "timestamp": datetime.now().isoformat()
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route("/api/sars/<string:num_sar>", methods=["PUT", "OPTIONS"])
def atualizar_sar_api(num_sar):
    """Endpoint para atualizar registro da ExecucaoSar"""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    dados = request.get_json()
    logging.info(f"✅ Atualizando ExecucaoSar {num_sar} via API com dados: {dados}")
    
    try:
        success = update_database_optimized(num_sar, 'generic_update', campos_atualizacao=dados)
        
        if success:
            # ✅ NOVA: Atualizar Excel/Redmine em background se status foi alterado
            if 'status' in dados:
                novo_status = dados['status']
                responsavel = dados.get('responsavelHub') or dados.get('responsavel')
                
                def update_secondary_systems():
                    try:
                        status_map = {
                            'Pendente': 1,
                            'Em Andamento': 2, 
                            'Concluído': 3,
                            'Cancelado': 5
                        }
                        
                        excel_future = executor.submit(update_excel_optimized, num_sar, novo_status, responsavel)
                        redmine_future = executor.submit(update_redmine_optimized, num_sar, status_map.get(novo_status, 1))
                        
                        excel_result = excel_future.result(timeout=30)
                        redmine_result = redmine_future.result(timeout=30)
                        
                        logging.info(f"SAR {num_sar} atualizado via API - Excel: {excel_result}, Redmine: {redmine_result}")
                        
                    except Exception as e:
                        logging.error(f"Erro ao atualizar sistemas secundários para SAR {num_sar}: {e}")
                
                executor.submit(update_secondary_systems)
            
            response = jsonify({
                "success": True,
                "mensagem": f"ExecucaoSar {num_sar} atualizado com sucesso"
            })
        else:
            response = jsonify({"erro": "Falha ao atualizar ExecucaoSar no banco de dados"})
            
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200 if success else 500
            
    except Exception as e:
        logging.error(f"Erro ao atualizar ExecucaoSar via API: {e}")
        error_response = jsonify({"erro": str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route("/health", methods=["GET"])
def health_check():
    """✅ MELHORADO: Endpoint para monitoramento da saúde da aplicação"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dbo.[ExecucaoSar]")
        count = cursor.fetchone()[0]
        cursor.close()
        return_connection(conn)
        
        return jsonify({
            "status": "healthy",
            "pool_available_connections": connection_pool.qsize(),
            "pool_max_size": connection_pool.maxsize,
            "total_execucaosar_no_banco": count,
            "excel_cache_age_seconds": round(time.time() - excel_cache_time, 2),
            "timestamp": datetime.now().isoformat(),
            "version": "2.0 - Com integração Excel/Redmine"
        })
    except Exception as e:
        logging.error(f"❌ Erro no health check ExecucaoSar: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ============= FUNÇÕES REDMINE LEGADAS (mantidas para compatibilidade) =============

def adicionar_comentario_redmine(id_redmine, comentario, autor="Sistema Automático"):
    try:
        if not id_redmine:
            return False, "ID do Redmine não fornecido"
        
        url = f"{REDMINE_URL_BASE}/issues/{id_redmine}.json"
        headers = {
            "Content-Type": "application/json",
            "X-Redmine-API-Key": REDMINE_API_KEY
        }
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        comentario_formatado = f"**[{timestamp}] - {autor}**\n\n{comentario}"
        
        payload = {"issue": {"notes": comentario_formatado}}
        
        response = requests.put(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logging.info(f"✅ Comentário adicionado com sucesso no Redmine #{id_redmine}")
            return True, "Comentário adicionado com sucesso"
        else:
            error_msg = f"Erro HTTP {response.status_code}: {response.text}"
            logging.error(f"❌ Erro ao adicionar comentário no Redmine #{id_redmine}: {error_msg}")
            return False, error_msg
    except Exception as e:
        error_msg = f"Erro ao conectar com Redmine: {str(e)}"
        logging.error(f"❌ {error_msg}")
        return False, error_msg

# ============= INICIALIZAÇÃO DA APLICAÇÃO =============

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('execucaosar_api.log')
        ]
    )
    
    logging.info("🚀 ========================================")
    logging.info("🚀 INICIANDO API EXECUCAOSAR v2.0")
    logging.info("🚀 Com integração Excel/Redmine completa")
    logging.info("🚀 ========================================")
    
    # Inicializar pool de conexões
    logging.info("🗄️ Inicializando pool de conexões do banco de dados...")
    try:
        init_connection_pool()
        logging.info("✅ Pool de conexões ExecucaoSar inicializado.")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao inicializar pool: {e}")
        logging.info("📝 Continuando sem pool, usando conexões individuais")
    
    # ✅ NOVA: Verificar se coluna ID_redmine existe
    logging.info("🔍 Verificando estrutura da tabela ExecucaoSar...")
    try:
        if verificar_coluna_id_redmine():
            logging.info("✅ Estrutura da tabela OK - Coluna ID_redmine encontrada")
        else:
            logging.warning("⚠️ Coluna ID_redmine não encontrada!")
            logging.warning("⚠️ Integração com Redmine pode não funcionar")
            logging.warning("⚠️ Execute: ALTER TABLE ExecucaoSar ADD ID_redmine INT")
    except Exception as e:
        logging.error(f"❌ Erro ao verificar estrutura da tabela: {e}")
    
    # Pré-carregar cache do Excel
    logging.info("📊 Pré-carregando cache do Excel...")
    try:
        get_cached_excel_data()
        logging.info("✅ Cache do Excel pré-carregado.")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao pré-carregar cache do Excel: {e}")
        logging.warning(f"⚠️ Verifique se o arquivo existe: {EXCEL_PATH}")
        logging.info("📝 Excel será carregado sob demanda")
    
    # Testar conectividade com Redmine
    logging.info("🌐 Testando conectividade com Redmine...")
    try:
        test_url = f"{REDMINE_URL_BASE}/issues.json?limit=1"
        response = requests.get(test_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            logging.info(f"✅ Redmine acessível em: {REDMINE_URL_BASE}")
        else:
            logging.warning(f"⚠️ Redmine retornou status {response.status_code}")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao testar Redmine: {e}")
        logging.warning("⚠️ Integração com Redmine pode não funcionar")
    
    logging.info("🌐 Iniciando servidor Flask ExecucaoSar na porta 5002...")
    logging.info("📋 ========================================")
    logging.info("📋 ENDPOINTS DISPONÍVEIS:")
    logging.info("📋 ========================================")
    logging.info("   🏠 GET  / - Status da API")
    logging.info("   🔧 GET  /test - Teste de conexão banco")
    logging.info("   🔧 GET  /test-redmine/:numsar - Teste integração Redmine")
    logging.info("   📊 GET  /api/sars - Lista todos os SARs")
    logging.info("   ✏️  PUT  /api/sars/:numsar - Atualiza SAR")
    logging.info("   👤 PUT  /sars/:numsar/assumir - Assumir SAR")
    logging.info("   🚫 PUT  /sars/:numsar/liberar - Liberar SAR")
    logging.info("   ✅ PUT  /sars/:numsar/finalizar - Finalizar (DELETE + Excel + Redmine)")
    logging.info("   ❌ PUT  /sars/:numsar/cancelar - Cancelar (DELETE + Excel + Redmine)")
    logging.info("   📝 GET  /sars/:numsar/observacoes - Buscar observações")
    logging.info("   ➕ PUT  /sars/:numsar/observacao - Adicionar observação")
    logging.info("   💚 GET  /health - Status da aplicação")
    logging.info("📋 ========================================")
    logging.info("🔗 TESTES RÁPIDOS:")
    logging.info("🔗   http://localhost:5002/test")
    logging.info("🔗   http://localhost:5002/health")
    logging.info("🔗   http://localhost:5002/test-redmine/SEU_NUMSAR")
    logging.info("📋 ========================================")
    
    app.run(debug=True, host='0.0.0.0', port=5002, threaded=True)