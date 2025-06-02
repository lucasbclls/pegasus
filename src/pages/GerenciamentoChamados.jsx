import React, { useState, useEffect } from 'react';
import ChamadoCard from '../components/ChamadoCard';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';
import axios from 'axios';

const GerenciamentoChamados = () => {
  const [chamados, setChamados] = useState([]);
  const [mensagem, setMensagem] = useState('');
  const [secaoExibida, setSecaoExibida] = useState('novos');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário', avatar: null };

  useEffect(() => {
    const buscarChamados = async () => {
      try {
        // ✅ CORRIGIDO: URL para a porta 5000 com /api/
        const response = await axios.get('http://127.0.0.1:5000/api/chamados');

        console.log('Dados recebidos da API:', response.data);

        // ✅ Buscar responsáveis E status salvos no localStorage
        const responsaveisSalvos = JSON.parse(localStorage.getItem('chamados_responsaveis')) || {};
        const statusSalvos = JSON.parse(localStorage.getItem('chamados_status')) || {};
        console.log('Responsáveis salvos no localStorage:', responsaveisSalvos);
        console.log('Status salvos no localStorage:', statusSalvos);

        const chamadosFormatados = response.data.map((chamado) => {
          // ✅ Usar responsável do localStorage se existir, senão usar da API
          const responsavelSalvo = responsaveisSalvos[chamado.id];
          const responsavelFinal = responsavelSalvo || chamado.responsavel || '';
          
          // ✅ NOVO: Usar status do localStorage se existir, senão usar da API
          const statusSalvo = statusSalvos[chamado.id];
          const statusFinal = statusSalvo || chamado.status || 'Pendente';
          
          if (responsavelSalvo) {
            console.log(`✅ Responsável restaurado para chamado ${chamado.id}: ${responsavelSalvo}`);
          }
          if (statusSalvo) {
            console.log(`✅ Status restaurado para chamado ${chamado.id}: ${statusSalvo}`);
          }

          return {
            id: chamado.id,
            nomeSolicitante: chamado.nomeSolicitante ?? '',
            telefone: chamado.telefone ?? '',
            emailSolicitante: chamado.emailSolicitante ?? '',
            empresa: chamado.empresa ?? '',
            cidade: chamado.cidade ?? '',
            tecnologia: chamado.tecnologia ?? '',
            nodeAfetadas: chamado.nodeAfetadas ?? '',
            tipoReclamacao: chamado.tipoReclamacao ?? '',
            detalhesProblema: chamado.detalhesProblema ?? '',
            testesRealizados: chamado.testesRealizados ?? '',
            modelEquipamento: chamado.modelEquipamento ?? '',
            baseAfetada: chamado.baseAfetada ?? '',
            contratosAfetados: chamado.contratosAfetados ?? '',
            servicoAfetado: chamado.servicoAfetado ?? '',
            dataEvento: chamado.dataEvento ?? null,
            horaInicio: chamado.horaInicio ?? null,
            horaConclusao: chamado.horaConclusao ?? null,
            status: statusFinal, // ✅ ALTERADO: usar status final (localStorage + API)
            prioridade: chamado.prioridade ?? 'Baixa',
            responsavel: responsavelFinal // ✅ Usar responsável final (localStorage + API)
          };
        });

        setChamados(chamadosFormatados);
      } catch (error) {
        console.error('Erro ao buscar chamados:', error);
        setMensagem('Erro ao carregar os chamados.');
      }
    };

    buscarChamados();
  }, []); // ← execute apenas uma vez ao montar o componente

  // ✅ FUNÇÃO CORRIGIDA para atualizar responsável + salvar no localStorage
  const atualizarResponsavel = (id, novoResponsavel) => {
    console.log(`🔄 Atualizando responsável - Chamado ${id}: ${novoResponsavel}`);
    
    // ✅ Salvar no localStorage para persistir entre reloads
    const responsaveisSalvos = JSON.parse(localStorage.getItem('chamados_responsaveis')) || {};
    
    if (novoResponsavel) {
      responsaveisSalvos[id] = novoResponsavel;
    } else {
      delete responsaveisSalvos[id]; // Remove se responsável for null/undefined
    }
    
    localStorage.setItem('chamados_responsaveis', JSON.stringify(responsaveisSalvos));
    console.log(`💾 Responsável salvo no localStorage - Chamado ${id}: ${novoResponsavel}`);
    
    setChamados((prevChamados) =>
      prevChamados.map((chamado) => {
        if (chamado.id === id) {
          console.log(`✅ Responsável atualizado - Chamado ${id}: de "${chamado.responsavel}" para "${novoResponsavel}"`);
          return { ...chamado, responsavel: novoResponsavel };
        }
        return chamado;
      })
    );
  };

  // ✅ FUNÇÃO CORRIGIDA para atualizar status e responsável + localStorage + Backend
  const atualizarStatusChamado = async (id, novoStatus, observacoes, novoResponsavel = null) => {
    console.log(`🔄 Atualizando status - Chamado ${id}:`, { novoStatus, novoResponsavel });
    
    try {
      // ✅ PRIMEIRO: Tentar salvar no backend
      const response = await axios.put(`http://127.0.0.1:5000/api/chamados/${id}`, {
        status: novoStatus,
        observacoes,
        responsavel: novoResponsavel
      });
      
      console.log('✅ Status salvo no backend:', response.data);
    } catch (error) {
      console.error('❌ Erro ao salvar no backend:', error);
      // Continua e salva no localStorage mesmo se o backend falhar
    }
    
    // ✅ BACKUP: Salvar status no localStorage
    const statusSalvos = JSON.parse(localStorage.getItem('chamados_status')) || {};
    statusSalvos[id] = novoStatus;
    localStorage.setItem('chamados_status', JSON.stringify(statusSalvos));
    console.log(`💾 Status salvo no localStorage - Chamado ${id}: ${novoStatus}`);
    
    // ✅ Atualizar localStorage de responsável se necessário
    if (novoResponsavel !== null) {
      const responsaveisSalvos = JSON.parse(localStorage.getItem('chamados_responsaveis')) || {};
      
      if (novoResponsavel) {
        responsaveisSalvos[id] = novoResponsavel;
      } else {
        delete responsaveisSalvos[id];
      }
      
      localStorage.setItem('chamados_responsaveis', JSON.stringify(responsaveisSalvos));
      console.log(`💾 Responsável salvo no localStorage via status - Chamado ${id}: ${novoResponsavel}`);
    }
    
    // ✅ Atualizar estado local
    setChamados((chamadosAnteriores) =>
      chamadosAnteriores.map((chamado) => {
        if (chamado.id === id) {
          const chamadoAtualizado = { 
            ...chamado, 
            status: novoStatus, 
            observacoes 
          };
          
          // Se foi passado um novo responsável, atualiza também
          if (novoResponsavel !== null) {
            chamadoAtualizado.responsavel = novoResponsavel;
          }
          
          console.log(`✅ Chamado ${id} atualizado:`, chamadoAtualizado);
          return chamadoAtualizado;
        }
        return chamado;
      })
    );

    // ✅ Mudar automaticamente para a aba correta
    if (novoStatus === 'Em Andamento') {
      setSecaoExibida('em-atendimento');
    } else if (novoStatus === 'Pendente') {
      setSecaoExibida('novos');
    }

    console.log(`Chamado ${id} atualizado para ${novoStatus}`);
  };

  const chamadosNovos = chamados.filter((chamado) => chamado.status === 'Pendente');
  const chamadosEmAtendimento = chamados.filter((chamado) => chamado.status === 'Em Andamento');

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
              Novos Chamados ({chamadosNovos.length})
            </button>
            <button
              className={`py-2 px-4 rounded ${secaoExibida === 'em-atendimento' ? 'bg-claro-red text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
              onClick={() => setSecaoExibida('em-atendimento')}
            >
              Em Atendimento ({chamadosEmAtendimento.length})
            </button>
          </div>

          {mensagem && <div className="bg-green-200 text-green-800 p-2 rounded mb-4">{mensagem}</div>}

          <div>
            <h2 className="text-xl font-semibold mb-4 text-text-gray">
              {secaoExibida === 'novos' ? 'Novos Chamados' : 'Chamados Em Atendimento'}
            </h2>

            {/* Exibição da lista de chamados por seção */}
            {secaoExibida === 'novos' ? (
              chamadosNovos.length === 0 ? (
                <p className="text-gray-600">Nenhum novo chamado encontrado.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {chamadosNovos.map((chamado) => (
                    <ChamadoCard
                      key={chamado.id}
                      chamado={chamado}
                      onAtualizarStatus={atualizarStatusChamado}
                      onAtualizarResponsavel={atualizarResponsavel}
                      usuario={usuarioLogado}
                    />
                  ))}
                </div>
              )
            ) : null}

            {secaoExibida === 'em-atendimento' ? (
              chamadosEmAtendimento.length === 0 ? (
                <p className="text-gray-600">Nenhum chamado em atendimento encontrado.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {chamadosEmAtendimento.map((chamado) => (
                    <ChamadoCard
                      key={chamado.id}
                      chamado={chamado}
                      onAtualizarStatus={atualizarStatusChamado}
                      onAtualizarResponsavel={atualizarResponsavel}
                      usuario={usuarioLogado}
                    />
                  ))}
                </div>
              )
            ) : null}
          </div>
        </main>
      </div>

      <Footer />
    </div>
  );
};

export default GerenciamentoChamados;