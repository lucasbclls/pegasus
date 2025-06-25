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
  const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário', avatar: null };

  useEffect(() => {
    const buscarSars = async () => {
      try {
        // TODO: Substituir por URL da API real de SARs
        // Para demonstração, vou simular dados
        const sarsMock = [
          {
            id: 1,
            numeroSar: "SAR2025001",
            titulo: "Instalação Fibra Óptica",
            tipoServico: "Instalação",
            cliente: "João Silva",
            endereco: "Rua das Flores, 123",
            bairro: "Centro",
            cidade: "Vitória",
            tecnologia: "FTTH",
            equipamento: "ONT Huawei",
            descricaoServico: "Instalação de internet fibra óptica 200MB",
            tempoEstimado: "2 horas",
            dataAgendamento: "2025-01-15",
            horaInicio: "08:00",
            horaConclusao: "",
            status: "Pendente",
            prioridade: "Alta",
            responsavel: ""
          },
          {
            id: 2,
            numeroSar: "SAR2025002",
            titulo: "Manutenção GPON",
            tipoServico: "Manutenção",
            cliente: "Maria Santos",
            endereco: "Av. Central, 456",
            bairro: "Jardins",
            cidade: "Vila Velha",
            tecnologia: "GPON",
            equipamento: "Splitter Óptico",
            descricaoServico: "Verificação e reparo de splitter óptico",
            tempoEstimado: "1.5 horas",
            dataAgendamento: "2025-01-15",
            horaInicio: "10:00",
            horaConclusao: "",
            status: "Em Andamento",
            prioridade: "Média",
            responsavel: "Técnico João"
          },
          {
            id: 3,
            numeroSar: "SAR2025003",
            titulo: "Upgrade de Velocidade",
            tipoServico: "Upgrade",
            cliente: "Pedro Costa",
            endereco: "Rua do Comércio, 789",
            bairro: "Praia da Costa",
            cidade: "Vila Velha",
            tecnologia: "FTTH",
            equipamento: "ONT Nokia",
            descricaoServico: "Upgrade de 100MB para 500MB",
            tempoEstimado: "1 hora",
            dataAgendamento: "2025-01-16",
            horaInicio: "14:00",
            horaConclusao: "",
            status: "Pendente",
            prioridade: "Baixa",
            responsavel: ""
          }
        ];

        console.log('SARs simulados carregados:', sarsMock);

        // Buscar responsáveis e status salvos no localStorage
        const responsaveisSalvos = JSON.parse(localStorage.getItem('sars_responsaveis')) || {};
        const statusSalvos = JSON.parse(localStorage.getItem('sars_status')) || {};

        const sarsFormatados = sarsMock.map((sar) => {
          const responsavelSalvo = responsaveisSalvos[sar.id];
          const responsavelFinal = responsavelSalvo || sar.responsavel || '';
          
          const statusSalvo = statusSalvos[sar.id];
          const statusFinal = statusSalvo || sar.status || 'Pendente';

          return {
            ...sar,
            status: statusFinal,
            responsavel: responsavelFinal
          };
        });

        setSars(sarsFormatados);
      } catch (error) {
        console.error('Erro ao buscar SARs:', error);
        setMensagem('Erro ao carregar os SARs.');
      }
    };

    buscarSars();
  }, []);

  // Função para atualizar responsável + salvar no localStorage
  const atualizarResponsavel = (id, novoResponsavel) => {
    const responsaveisSalvos = JSON.parse(localStorage.getItem('sars_responsaveis')) || {};
    
    if (novoResponsavel) {
      responsaveisSalvos[id] = novoResponsavel;
    } else {
      delete responsaveisSalvos[id];
    }
    
    localStorage.setItem('sars_responsaveis', JSON.stringify(responsaveisSalvos));
    
    setSars((prevSars) =>
      prevSars.map((sar) => {
        if (sar.id === id) {
          return { ...sar, responsavel: novoResponsavel };
        }
        return sar;
      })
    );
  };

  // Função para atualizar status
  const atualizarStatusSar = async (id, novoStatus, observacoes, novoResponsavel = null) => {
    // Salvar status no localStorage
    const statusSalvos = JSON.parse(localStorage.getItem('sars_status')) || {};
    statusSalvos[id] = novoStatus;
    localStorage.setItem('sars_status', JSON.stringify(statusSalvos));
    
    // Atualizar localStorage de responsável se necessário
    if (novoResponsavel !== null) {
      const responsaveisSalvos = JSON.parse(localStorage.getItem('sars_responsaveis')) || {};
      
      if (novoResponsavel) {
        responsaveisSalvos[id] = novoResponsavel;
      } else {
        delete responsaveisSalvos[id];
      }
      
      localStorage.setItem('sars_responsaveis', JSON.stringify(responsaveisSalvos));
    }
    
    // Atualizar estado local
    setSars((sarsAnteriores) =>
      sarsAnteriores.map((sar) => {
        if (sar.id === id) {
          const sarAtualizado = { 
            ...sar, 
            status: novoStatus, 
            observacoes 
          };
          
          if (novoResponsavel !== null) {
            sarAtualizado.responsavel = novoResponsavel;
          }
          
          return sarAtualizado;
        }
        return sar;
      })
    );

    // Mudar automaticamente para a aba correta
    if (novoStatus === 'Em Andamento') {
      setSecaoExibida('em-execucao');
    } else if (novoStatus === 'Pendente') {
      setSecaoExibida('novos');
    }
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

          {mensagem && <div className="bg-green-200 text-green-800 p-2 rounded mb-4">{mensagem}</div>}

          <div>
            <h2 className="text-xl font-semibold mb-4 text-text-gray">
              {secaoExibida === 'novos' ? 'Novos SARs' : 'SARs Em Execução'}
            </h2>

            {secaoExibida === 'novos' ? (
              sarsNovos.length === 0 ? (
                <p className="text-gray-600">Nenhum novo SAR encontrado.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {sarsNovos.map((sar) => (
                    <SarCard
                      key={sar.id}
                      sar={sar}
                      onAtualizarStatus={atualizarStatusSar}
                      onAtualizarResponsavel={atualizarResponsavel}
                      usuario={usuarioLogado}
                    />
                  ))}
                </div>
              )
            ) : null}

            {secaoExibida === 'em-execucao' ? (
              sarsEmExecucao.length === 0 ? (
                <p className="text-gray-600">Nenhum SAR em execução encontrado.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {sarsEmExecucao.map((sar) => (
                    <SarCard
                      key={sar.id}
                      sar={sar}
                      onAtualizarStatus={atualizarStatusSar}
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

export default ExecucaoSar;