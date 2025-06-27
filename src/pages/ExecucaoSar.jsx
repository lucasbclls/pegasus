import React, { useState, useEffect } from 'react';
import SarCard from '../components/SarCard';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';
import axios from 'axios';

const ExecucaoSar = () => {
  const [sars, setSars] = useState([]);
  const [mensagem, setMensagem] = useState('');
  const [secaoExibida, setSecaoExibida] = useState('novos');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário', avatar: null };

  useEffect(() => {
    const buscarSars = async () => {
      setLoading(true);
      try {
        console.log('🔄 Buscando SARs da API ExecucaoSar...');
        
        // ✅ Conectar com a API real do backend SAR
        const response = await axios.get('http://localhost:5007/api/sars');

        console.log('✅ Dados recebidos da API ExecucaoSar:', response.data);

        // ✅ Buscar responsáveis e status salvos no localStorage (usando NumSar como chave)
        const responsaveisSalvos = JSON.parse(localStorage.getItem('execucaosar_responsaveis')) || {};
        const statusSalvos = JSON.parse(localStorage.getItem('execucaosar_status')) || {};
        console.log('📦 Responsáveis salvos no localStorage:', responsaveisSalvos);
        console.log('📦 Status salvos no localStorage:', statusSalvos);

        const sarsFormatados = response.data.map((sar) => {
          // ✅ Usar NumSar como chave única
          const chaveUnica = sar.numeroSar || sar.NumSar;
          
          // ✅ Usar responsável do localStorage se existir, senão usar da API
          const responsavelSalvo = responsaveisSalvos[chaveUnica];
          const responsavelFinal = responsavelSalvo || sar.responsavel || sar.responsavelHub || sar.responsavelDTC || '';
          
          // ✅ Usar status do localStorage se existir, senão usar da API
          const statusSalvo = statusSalvos[chaveUnica];
          const statusFinal = statusSalvo || sar.status || 'Pendente';
          
          if (responsavelSalvo) {
            console.log(`✅ Responsável restaurado para SAR ${chaveUnica}: ${responsavelSalvo}`);
          }
          if (statusSalvo) {
            console.log(`✅ Status restaurado para SAR ${chaveUnica}: ${statusSalvo}`);
          }

          return {
            // ✅ Campos adaptados para ExecucaoSar
            id: chaveUnica, // Usar NumSar como ID
            numeroSar: chaveUnica,
            titulo: sar.titulo || `${sar.acao || 'Serviço'} - ${sar.areaTecnica || 'Técnico'}`,
            tipoServico: sar.tipoServico || sar.acao || '',
            cliente: sar.cliente || '', // Não existe na ExecucaoSar
            endereco: sar.endereco || sar.enderecoNap || '',
            bairro: sar.bairro || '', // Não existe na ExecucaoSar
            cidade: sar.cidade || '',
            tecnologia: sar.tecnologia || sar.areaTecnica || '',
            equipamento: sar.equipamento || (sar.quantPort ? `${sar.quantPort} portas` : ''),
            descricaoServico: sar.descricaoServico || sar.caminho || '',
            tempoEstimado: sar.tempoEstimado || '', // Não existe na ExecucaoSar
            dataAgendamento: sar.dataAgendamento || sar.dataSolicitacao || null,
            horaInicio: sar.horaInicio || null, // Não existe na ExecucaoSar
            horaConclusao: sar.horaConclusao || sar.dataExecucao || null,
            status: statusFinal, // ✅ Usar status final (localStorage + API)
            prioridade: sar.prioridade || 'Normal', // Não existe na ExecucaoSar
            responsavel: responsavelFinal, // ✅ Usar responsável final (localStorage + API)
            observacoes: sar.observacoes || '', // Não existe na ExecucaoSar
            // ✅ Campos específicos da ExecucaoSar
            designacao: sar.designacao || '',
            quantPort: sar.quantPort || 0,
            caminho: sar.caminho || '',
            dataVenc: sar.dataVenc || null,
            dataCancelamento: sar.dataCancelamento || null,
            idadeExecucao: sar.idadeExecucao || 0,
            anoMes: sar.anoMes || null,
            responsavelHub: sar.responsavelHub || '',
            responsavelDTC: sar.responsavelDTC || '',
            acao: sar.acao || '',
            areaTecnica: sar.areaTecnica || ''
          };
        });

        setSars(sarsFormatados);
        setMensagem('');
        console.log(`✅ ${sarsFormatados.length} SARs carregados com sucesso da ExecucaoSar!`);

      } catch (error) {
        console.error('❌ Erro ao buscar SARs da ExecucaoSar:', error);
        
        // ✅ Não usar dados simulados - mostrar erro real
        setSars([]);
        setMensagem('❌ Erro ao conectar com o banco de dados. Verifique se o servidor está rodando na porta 5002.');
        
        console.log('❌ Falha na conexão com API ExecucaoSar. Nenhum dado será exibido.');
      } finally {
        setLoading(false);
      }
    };

    buscarSars();
  }, []); // ← execute apenas uma vez ao montar o componente

  // ✅ Função para recarregar SARs (usada em conflitos de responsável)
  const recarregarSars = async () => {
    console.log('🔄 Recarregando SARs da ExecucaoSar...');
    try {
      const response = await axios.get('http://localhost:5007/api/sars');
      const sarsAtualizados = response.data.map((sar) => {
        const chaveUnica = sar.numeroSar || sar.NumSar;
        
        return {
          id: chaveUnica,
          numeroSar: chaveUnica,
          titulo: sar.titulo || `${sar.acao || 'Serviço'} - ${sar.areaTecnica || 'Técnico'}`,
          tipoServico: sar.tipoServico || sar.acao || '',
          cliente: sar.cliente || '',
          endereco: sar.endereco || sar.enderecoNap || '',
          bairro: sar.bairro || '',
          cidade: sar.cidade || '',
          tecnologia: sar.tecnologia || sar.areaTecnica || '',
          equipamento: sar.equipamento || (sar.quantPort ? `${sar.quantPort} portas` : ''),
          descricaoServico: sar.descricaoServico || sar.caminho || '',
          tempoEstimado: sar.tempoEstimado || '',
          dataAgendamento: sar.dataAgendamento || sar.dataSolicitacao || null,
          horaInicio: sar.horaInicio || null,
          horaConclusao: sar.horaConclusao || sar.dataExecucao || null,
          status: sar.status || 'Pendente',
          prioridade: sar.prioridade || 'Normal',
          responsavel: sar.responsavel || sar.responsavelHub || sar.responsavelDTC || '',
          observacoes: sar.observacoes || '',
          // Campos específicos ExecucaoSar
          designacao: sar.designacao || '',
          quantPort: sar.quantPort || 0,
          caminho: sar.caminho || '',
          dataVenc: sar.dataVenc || null,
          dataCancelamento: sar.dataCancelamento || null,
          idadeExecucao: sar.idadeExecucao || 0,
          anoMes: sar.anoMes || null,
          responsavelHub: sar.responsavelHub || '',
          responsavelDTC: sar.responsavelDTC || '',
          acao: sar.acao || '',
          areaTecnica: sar.areaTecnica || ''
        };
      });
      setSars(sarsAtualizados);
      console.log('✅ SARs da ExecucaoSar recarregados com sucesso');
    } catch (error) {
      console.error('❌ Erro ao recarregar SARs da ExecucaoSar:', error);
      setMensagem('❌ Erro ao recarregar dados do banco. Verifique a conexão.');
    }
  };

  // ✅ Função para atualizar responsável + salvar no localStorage + Backend
  // 🔧 SUBSTITUIR a função atualizarResponsavel no ExecucaoSar.jsx (linha ~164)

const atualizarResponsavel = async (numeroSar, novoResponsavel) => {
  console.log(`🔄 Atualizando responsável ExecucaoSar - SAR ${numeroSar}: ${novoResponsavel}`);
  
  try {
    // ✅ CORREÇÃO: Verificar se é assumir ou liberar
    let response;
    
    if (novoResponsavel === null || novoResponsavel === 'null' || !novoResponsavel) {
      // 🔓 LIBERAR - responsável é null
      console.log(`🔓 Liberando SAR ${numeroSar}`);
      response = await axios.put(`http://localhost:5007/sars/${numeroSar}/liberar`, {
        apenas_visual: false
      });
    } else {
      // 🙋‍♂️ ASSUMIR - responsável tem valor
      console.log(`🙋‍♂️ Assumindo SAR ${numeroSar} para ${novoResponsavel}`);
      response = await axios.put(`http://localhost:5007/sars/${numeroSar}/assumir`, {
        responsavel: novoResponsavel,
        apenas_visual: false
      });
    }
    
    console.log('✅ Responsável salvo no backend ExecucaoSar:', response.data);
  } catch (error) {
    console.error('❌ Erro ao salvar responsável no backend ExecucaoSar:', error);
    // Continua e salva no localStorage mesmo se o backend falhar
  }
  
  // ✅ BACKUP: Salvar responsável no localStorage (usando NumSar como chave)
  const responsaveisSalvos = JSON.parse(localStorage.getItem('execucaosar_responsaveis')) || {};
  
  if (novoResponsavel) {
    responsaveisSalvos[numeroSar] = novoResponsavel;
  } else {
    delete responsaveisSalvos[numeroSar]; // Remove se responsável for null/undefined
  }
  
  localStorage.setItem('execucaosar_responsaveis', JSON.stringify(responsaveisSalvos));
  console.log(`💾 Responsável ExecucaoSar salvo no localStorage - SAR ${numeroSar}: ${novoResponsavel}`);
  
  // ✅ Atualizar estado local
  setSars((prevSars) =>
    prevSars.map((sar) => {
      if (sar.numeroSar === numeroSar) {
        console.log(`✅ Responsável ExecucaoSar atualizado - SAR ${numeroSar}: de "${sar.responsavel}" para "${novoResponsavel}"`);
        
        // Atualizar o responsável geral
        return { 
          ...sar, 
          responsavel: novoResponsavel 
        };
      }
      return sar;
    })
  );
};

  // ✅ Função para atualizar status + localStorage + Backend
  const atualizarStatusSar = async (numeroSar, novoStatus, observacoes, novoResponsavel = null) => {
    console.log(`🔄 Atualizando status ExecucaoSar - SAR ${numeroSar}:`, { novoStatus, novoResponsavel });
    
    try {
      // ✅ PRIMEIRO: Tentar salvar no backend ExecucaoSar
      const response = await axios.put(`http://localhost:5007/api/sars/${numeroSar}`, {
        status: novoStatus,
        observacoes,
        responsavel: novoResponsavel
      });
      
      console.log('✅ Status ExecucaoSar salvo no backend:', response.data);
    } catch (error) {
      console.error('❌ Erro ao salvar status no backend ExecucaoSar:', error);
      // Continua e salva no localStorage mesmo se o backend falhar
    }
    
    // ✅ BACKUP: Salvar status no localStorage (usando NumSar como chave)
    const statusSalvos = JSON.parse(localStorage.getItem('execucaosar_status')) || {};
    statusSalvos[numeroSar] = novoStatus;
    localStorage.setItem('execucaosar_status', JSON.stringify(statusSalvos));
    console.log(`💾 Status ExecucaoSar salvo no localStorage - SAR ${numeroSar}: ${novoStatus}`);
    
    // ✅ Atualizar localStorage de responsável se necessário
    if (novoResponsavel !== null) {
      const responsaveisSalvos = JSON.parse(localStorage.getItem('execucaosar_responsaveis')) || {};
      
      if (novoResponsavel) {
        responsaveisSalvos[numeroSar] = novoResponsavel;
      } else {
        delete responsaveisSalvos[numeroSar];
      }
      
      localStorage.setItem('execucaosar_responsaveis', JSON.stringify(responsaveisSalvos));
      console.log(`💾 Responsável ExecucaoSar salvo no localStorage via status - SAR ${numeroSar}: ${novoResponsavel}`);
    }
    
    // ✅ Atualizar estado local
    setSars((sarsAnteriores) =>
      sarsAnteriores.map((sar) => {
        if (sar.numeroSar === numeroSar) {
          const sarAtualizado = { 
            ...sar, 
            status: novoStatus, 
            observacoes 
          };
          
          // Se foi passado um novo responsável, atualiza também
          if (novoResponsavel !== null) {
            sarAtualizado.responsavel = novoResponsavel;
          }
          
          console.log(`✅ ExecucaoSar ${numeroSar} atualizado:`, sarAtualizado);
          return sarAtualizado;
        }
        return sar;
      })
    );

    // ✅ Mudar automaticamente para a aba correta
    if (novoStatus === 'Em Andamento') {
      setSecaoExibida('em-execucao');
    } else if (novoStatus === 'Pendente') {
      setSecaoExibida('novos');
    }

    console.log(`ExecucaoSar ${numeroSar} atualizado para ${novoStatus}`);
  };

  const sarsNovos = sars.filter((sar) => sar.status === 'Pendente');
  const sarsEmExecucao = sars.filter((sar) => sar.status === 'Em Andamento');

  const openSidebar = () => setSidebarOpen(true);
  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  return (
    <div className="flex flex-col min-h-screen">
      <Header onToggleSidebar={toggleSidebar} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={sidebarOpen} onMouseEnter={openSidebar} onMouseLeave={closeSidebar} />

        <main className={`flex-1 p-4 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
          <div className="mb-4 flex space-x-2 justify-center">
            <button
              className={`py-2 px-4 rounded ${secaoExibida === 'novos' ? 'bg-claro-red text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
              onClick={() => setSecaoExibida('novos')}
            >
              Novos SARs ({sarsNovos.length})
            </button>
            <button
              className={`py-2 px-4 rounded ${secaoExibida === 'em-execucao' ? 'bg-claro-red text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
              onClick={() => setSecaoExibida('em-execucao')}
            >
              Em Execução ({sarsEmExecucao.length})
            </button>
          </div>

          {mensagem && (
            <div className={`${
              mensagem.includes('Erro') ? 'bg-red-200 text-red-800 border border-red-300' : 
              mensagem.includes('offline') ? 'bg-yellow-200 text-yellow-800 border border-yellow-300' : 
              'bg-green-200 text-green-800 border border-green-300'
            } p-4 rounded-lg mb-4`}>
              <div className="flex items-center space-x-2">
                {mensagem.includes('Erro') ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                )}
                <span className="font-medium">{mensagem}</span>
              </div>
              {mensagem.includes('Erro') && (
                <div className="mt-2 text-sm">
                  <p><strong>Possíveis soluções:</strong></p>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Verifique se o servidor backend está rodando na porta 5002</li>
                    <li>Confirme se o banco de dados está acessível</li>
                    <li>Execute: <code className="bg-red-100 px-1 rounded">python app.py</code> no diretório do backend</li>
                  </ul>
                </div>
              )}
            </div>
          )}

          {loading ? (
            <div className="flex justify-center items-center py-12">
              <div className="flex flex-col items-center space-y-4">
                <svg className="animate-spin h-8 w-8 text-claro-red" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-3.647z"/>
                </svg>
                <div className="text-center">
                  <span className="text-lg font-medium text-gray-700">Carregando SARs...</span>
                  <p className="text-sm text-gray-500 mt-1">Conectando com banco de dados ExecucaoSar</p>
                </div>
              </div>
            </div>
          ) : (
            <div>
              <h2 className="text-xl font-semibold mb-4 text-text-gray">
                {secaoExibida === 'novos' ? 'Novos SARs' : 'SARs Em Execução'}
              </h2>

              {secaoExibida === 'novos' ? (
                sarsNovos.length === 0 ? (
                  <div className="text-center py-8">
                    {mensagem.includes('Erro') ? (
                      <div className="text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7l-1.5-1.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-lg font-medium text-gray-600">Não foi possível carregar os SARs</p>
                        <p className="text-sm text-gray-500 mt-2">Verifique a conexão com o banco de dados</p>
                      </div>
                    ) : (
                      <div className="text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7l-1.5-1.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-lg font-medium text-gray-600">Nenhum novo SAR encontrado</p>
                        <p className="text-sm text-gray-500 mt-2">Todos os SARs estão sendo executados ou já foram finalizados</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {sarsNovos.map((sar) => (
                      <SarCard
                        key={sar.numeroSar}
                        sar={sar}
                        onAtualizarStatus={atualizarStatusSar}
                        onAtualizarResponsavel={atualizarResponsavel}
                        onRecarregarSars={recarregarSars}
                        usuario={usuarioLogado}
                      />
                    ))}
                  </div>
                )
              ) : null}

              {secaoExibida === 'em-execucao' ? (
                sarsEmExecucao.length === 0 ? (
                  <div className="text-center py-8">
                    {mensagem.includes('Erro') ? (
                      <div className="text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7l-1.5-1.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-lg font-medium text-gray-600">Não foi possível carregar os SARs</p>
                        <p className="text-sm text-gray-500 mt-2">Verifique a conexão com o banco de dados</p>
                      </div>
                    ) : (
                      <div className="text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <p className="text-lg font-medium text-gray-600">Nenhum SAR em execução</p>
                        <p className="text-sm text-gray-500 mt-2">Todos os SARs estão pendentes ou já foram finalizados</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {sarsEmExecucao.map((sar) => (
                      <SarCard
                        key={sar.numeroSar}
                        sar={sar}
                        onAtualizarStatus={atualizarStatusSar}
                        onAtualizarResponsavel={atualizarResponsavel}
                        onRecarregarSars={recarregarSars}
                        usuario={usuarioLogado}
                      />
                    ))}
                  </div>
                )
              ) : null}
            </div>
          )}
        </main>
      </div>

      <Footer />
    </div>
  );
};

export default ExecucaoSar;