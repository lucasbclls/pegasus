import React, { useState, useEffect, useRef } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import axios from "axios";

const SarCard = ({ 
  sar, 
  onAtualizarStatus, 
  onAtualizarResponsavel, 
  onRecarregarSars,   
  usuario 
}) => {
  const {
    id, // numeroSar da ExecucaoSar
    numeroSar,
    titulo,
    status: currentStatus = "Pendente",
    prioridade = "Normal",
    responsavel,
    tipoServico,
    equipamento,
    cliente,
    endereco,
    bairro,
    cidade,
    tecnologia,
    descricaoServico,
    tempoEstimado,
    dataAgendamento,
    horaInicio,
    horaConclusao,
    // Campos específicos da ExecucaoSar
    designacao,
    quantPort,
    caminho,
    dataVenc,
    dataCancelamento,
    idadeExecucao,
    anoMes,
    responsavelHub,
    responsavelDTC,
    acao,
    areaTecnica
  } = sar;

  // Função para gerar avatar com iniciais
  const generateAvatar = (nome) => {
    if (!nome) return "U";
    const iniciais = nome
      .split(" ")
      .map((palavra) => palavra.charAt(0).toUpperCase())
      .slice(0, 2)
      .join("");
    return iniciais;
  };

  // Função para gerar cor do avatar baseada no nome
  const getAvatarColor = (nome) => {
    if (!nome) return "bg-gray-500";
    const colors = [
      "bg-red-500",
      "bg-blue-500",
      "bg-green-500",
      "bg-yellow-500",
      "bg-purple-500",
      "bg-pink-500",
      "bg-indigo-500",
      "bg-teal-500",
    ];
    let hash = 0;
    for (let i = 0; i < nome.length; i++) {
      hash = nome.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  const [novoStatus, setNovoStatus] = useState(currentStatus);
  const [confirmarStatus, setConfirmarStatus] = useState(false);
  const [isObservacoesOpen, setIsObservacoesOpen] = useState(false);
  const [novaObservacaoTexto, setNovaObservacaoTexto] = useState("");

  // Estados para modal de fechamento
  const [showModalFechamento, setShowModalFechamento] = useState(false);
  const [observacaoFechamento, setObservacaoFechamento] = useState("");
  const [loadingFechamento, setLoadingFechamento] = useState(false);

  // Estados para observações
  const [historicoObservacoes, setHistoricoObservacoes] = useState([]);
  const [loadingObservacoes, setLoadingObservacoes] = useState(true);
  const [errorObservacoes, setErrorObservacoes] = useState(null);

  // Estados para assumir SAR
  const [responsavelAtual, setResponsavelAtual] = useState(responsavel);
  const [loadingAssumir, setLoadingAssumir] = useState(false);

  const popoverContainerRef = useRef(null);
  const [openAbove, setOpenAbove] = useState(false);

  // ✅ Função para obter URL do backend funcionando
  const getBackendUrl = () => {
    return localStorage.getItem('backend_url') || 'http://localhost:5002';
  };

  // useEffect para sincronizar com as props
  useEffect(() => {
    if (responsavel !== responsavelAtual) {
      console.log('SarCard ExecucaoSar - Atualizando responsável:', {
        numeroSar: numeroSar,
        responsavelProp: responsavel,
        responsavelAtual: responsavelAtual,
        atualizando: true
      });
      setResponsavelAtual(responsavel);
    }
  }, [responsavel, numeroSar]);

  // useEffect para carregar observações salvas no localStorage
  useEffect(() => {
    const carregarObservacoesSalvas = () => {
      try {
        const observacoesSalvas = localStorage.getItem(`observacoes_${numeroSar}`);
        if (observacoesSalvas) {
          const observacoesParsed = JSON.parse(observacoesSalvas);
          setHistoricoObservacoes(observacoesParsed);
          console.log(`✅ Observações carregadas do localStorage para SAR ${numeroSar}:`, observacoesParsed);
        }
      } catch (error) {
        console.error('Erro ao carregar observações do localStorage:', error);
      } finally {
        setLoadingObservacoes(false);
      }
    };

    if (numeroSar) {
      carregarObservacoesSalvas();
    }
  }, [numeroSar]);

  // Função para salvar observações no localStorage
  const salvarObservacoesLocalStorage = (observacoes) => {
    try {
      localStorage.setItem(`observacoes_${numeroSar}`, JSON.stringify(observacoes));
      console.log(`💾 Observações salvas no localStorage para SAR ${numeroSar}:`, observacoes);
    } catch (error) {
      console.error('Erro ao salvar observações no localStorage:', error);
    }
  };

  // Função para carregar observações do backend
  const carregarObservacoes = async () => {
    setLoadingObservacoes(true);
    setErrorObservacoes(null);
    try {
      // TODO: Implementar chamada para API de observações da ExecucaoSar
      // Por enquanto, as observações já estão carregadas do localStorage no useEffect
      console.log('Observações já carregadas do localStorage');
    } catch (err) {
      console.error("Falha ao carregar observações:", err);
      setErrorObservacoes("Não foi possível carregar as observações.");
    } finally {
      setLoadingObservacoes(false);
    }
  };

  useEffect(() => {
    if (isObservacoesOpen && popoverContainerRef.current) {
      const rect = popoverContainerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const popoverEstimatedHeight = 300;
      setOpenAbove(
        spaceBelow < popoverEstimatedHeight && rect.top > popoverEstimatedHeight
      );
    }
  }, [isObservacoesOpen]);

  // Função para mostrar notificação visual
  const mostrarNotificacao = (mensagem, tipo = 'success') => {
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(notification => notification.remove());

    const notification = document.createElement('div');
    notification.className = `notification-toast fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full`;
    
    if (tipo === 'success') {
      notification.classList.add('bg-green-500', 'text-white');
    } else if (tipo === 'error') {
      notification.classList.add('bg-red-500', 'text-white');
    } else {
      notification.classList.add('bg-blue-500', 'text-white');
    }
    
    notification.textContent = mensagem;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.classList.remove('translate-x-full');
    }, 100);

    setTimeout(() => {
      notification.classList.add('translate-x-full');
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, 3000);
  };

  // Função para assumir o SAR
  // 🔧 CORREÇÃO 1: Mover a atualização do estado para DEPOIS da requisição bem-sucedida

// Função para liberar o SAR - CORRIGIDA
const handleLiberarSar = async () => {
  setLoadingAssumir(true);
  try {
    // ✅ Primeiro faz a requisição para o backend
    const backendUrl = getBackendUrl();
    const response = await axios.put(`${backendUrl}/sars/${numeroSar}/liberar`, {
      apenas_visual: false
    });

    console.log('✅ SAR liberado no backend ExecucaoSar:', response.data);
    
    // ✅ SÓ ATUALIZA O ESTADO APÓS SUCESSO
    setResponsavelAtual(null);
    
    if (onAtualizarResponsavel) {
      onAtualizarResponsavel(numeroSar, null);
    }
    
    mostrarNotificacao("✅ SAR liberado com sucesso!", 'success');
    
  } catch (error) {
    console.error("❌ Erro ao liberar SAR ExecucaoSar:", error);
    mostrarNotificacao(`❌ Erro ao liberar SAR: ${error.response?.data?.erro || error.message}`, 'error');
    // ✅ Em caso de erro, mantém o estado atual
  } finally {
    setLoadingAssumir(false);
  }
};

// Função para assumir o SAR - CORRIGIDA  
const handleAssumirSar = async () => {
  // ✅ Validação extra para evitar assumir com responsável null
  if (temResponsavel) {
    mostrarNotificacao(`Este SAR já foi assumido por ${responsavelAtual}`, 'error');
    return;
  }

  setLoadingAssumir(true);
  const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário' };

  // ✅ Validação extra
  if (!usuarioLogado.nome || usuarioLogado.nome === 'null' || usuarioLogado.nome === null) {
    mostrarNotificacao('❌ Erro: Usuário não identificado', 'error');
    setLoadingAssumir(false);
    return;
  }

  try {
    // ✅ Primeiro faz a requisição para o backend
    const backendUrl = getBackendUrl();
    const response = await axios.put(`${backendUrl}/sars/${numeroSar}/assumir`, {
      responsavel: usuarioLogado.nome,
      apenas_visual: false
    });

    console.log('✅ SAR assumido no backend ExecucaoSar:', response.data);
    
    // ✅ SÓ ATUALIZA O ESTADO APÓS SUCESSO
    const nomeUsuario = usuarioLogado.nome;
    setResponsavelAtual(nomeUsuario);
    
    if (onAtualizarResponsavel) {
      onAtualizarResponsavel(numeroSar, nomeUsuario);
    }
    
    mostrarNotificacao(`✅ SAR assumido por ${nomeUsuario}!`, 'success');
    
  } catch (error) {
    console.error("❌ Erro ao assumir SAR ExecucaoSar:", error);
    mostrarNotificacao(`❌ Erro ao assumir SAR: ${error.response?.data?.erro || error.message}`, 'error');
    // ✅ Em caso de erro, mantém o estado atual
  } finally {
    setLoadingAssumir(false);
  }
};



  const handleStatusChange = (event) => {
    const novoStatusSelecionado = event.target.value;
    setNovoStatus(novoStatusSelecionado);
    
    if (novoStatusSelecionado === "Concluído") {
      setShowModalFechamento(true);
    } else {
      setConfirmarStatus(true);
    }
  };

  // Função para processar o fechamento com observação
  const handleConfirmarFechamento = async () => {
    if (observacaoFechamento.trim() === "") {
      mostrarNotificacao("Por favor, adicione uma observação de fechamento.", 'error');
      return;
    }

    setLoadingFechamento(true);
    try {
      // ✅ Adicionar observação de fechamento ao histórico
      const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Sistema' };
      const observacaoFinal = {
        usuario: usuarioLogado.nome,
        observacao: `🏁 SAR FINALIZADO: ${observacaoFechamento.trim()}`,
        data: new Date().toISOString(),
        timestamp: new Date().toISOString()
      };

      const observacoesAtualizadas = [...historicoObservacoes, observacaoFinal];
      setHistoricoObservacoes(observacoesAtualizadas);
      
      // ✅ Salvar no localStorage
      salvarObservacoesLocalStorage(observacoesAtualizadas);

      // ✅ Integração com API ExecucaoSar para finalizar - APENAS dados reais
      const backendUrl = getBackendUrl();
      const response = await axios.put(`${backendUrl}/sars/${numeroSar}/finalizar`, {
  observacao: observacaoFechamento.trim()
});
      console.log('✅ SAR finalizado no backend ExecucaoSar:', response.data);
      
      setShowModalFechamento(false);
      setObservacaoFechamento("");
      onAtualizarStatus?.(numeroSar, "Concluído", observacoesAtualizadas, responsavelAtual);
      mostrarNotificacao("✅ SAR finalizado com sucesso!", 'success');
    } catch (error) {
      console.error("❌ Erro ao finalizar SAR ExecucaoSar:", error);
      mostrarNotificacao(`❌ Erro ao finalizar SAR: ${error.response?.data?.erro || error.message}`, 'error');
    } finally {
      setLoadingFechamento(false);
    }
  };

  const handleCancelarFechamento = () => {
    setShowModalFechamento(false);
    setObservacaoFechamento("");
    setNovoStatus(currentStatus);
  };

  const handleConfirmarStatus = async () => {
    try {
      // ✅ Integração com API ExecucaoSar para atualizar status - APENAS dados reais
      const backendUrl = getBackendUrl();
      if (novoStatus === "Cancelado") {
        const response = await axios.put(`${backendUrl}/sars/${numeroSar}/cancelar`);
        console.log('✅ SAR cancelado no backend ExecucaoSar:', response.data);
      } else {
        const response = await axios.put(`${backendUrl}/api/sars/${numeroSar}`, {
          status: novoStatus
        });
        console.log('✅ Status SAR atualizado no backend ExecucaoSar:', response.data);
      }
      
      setConfirmarStatus(false);
      onAtualizarStatus?.(numeroSar, novoStatus, historicoObservacoes, responsavelAtual);
      mostrarNotificacao(`✅ Status atualizado para: ${novoStatus}`, 'success');
    } catch (error) {
      console.error("❌ Erro ao atualizar status ExecucaoSar:", error);
      mostrarNotificacao(`❌ Erro ao atualizar status: ${error.response?.data?.erro || error.message}`, 'error');
    }
  };

  const handleCancelarStatus = () => {
    setNovoStatus(currentStatus);
    setConfirmarStatus(false);
  };

  const handleToggleObservacoes = () => {
    setIsObservacoesOpen((prev) => {
      const newState = !prev;
      // Não precisa mais carregar do backend já que carregamos do localStorage no useEffect
      return newState;
    });
  };

  const handleAdicionarObservacao = async () => {
    if (novaObservacaoTexto.trim() === "") {
      mostrarNotificacao("Por favor, digite uma observação.", 'error');
      return;
    }

    try {
      const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Sistema' };
      const novaObservacao = {
        usuario: usuarioLogado.nome,
        observacao: novaObservacaoTexto.trim(),
        data: new Date().toISOString(),
        timestamp: new Date().toISOString()
      };

      // ✅ Atualizar estado local
      const observacoesAtualizadas = [...historicoObservacoes, novaObservacao];
      setHistoricoObservacoes(observacoesAtualizadas);
      
      // ✅ Salvar no localStorage para persistir após F5
      salvarObservacoesLocalStorage(observacoesAtualizadas);
      
      // TODO: Aqui você pode implementar chamada para API se necessário
      // await axios.post(`http://127.0.0.1:5002/sars/${numeroSar}/observacao`, novaObservacao);
      
      setNovaObservacaoTexto("");
      mostrarNotificacao("Observação adicionada com sucesso!", 'success');
      
      console.log(`✅ Nova observação adicionada ao SAR ${numeroSar}:`, novaObservacao);
    } catch (error) {
      console.error('Erro ao adicionar observação:', error);
      mostrarNotificacao("Erro ao adicionar observação", 'error');
    }
  };

  const prioridadeCores = {
    Alta: "bg-claro-red text-white",
    Média: "bg-yellow-500 text-white",
    Normal: "bg-blue-500 text-white", 
    Baixa: "bg-green-500 text-white",
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    try {
      const date = new Date(dateString);
      return format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });
    } catch (error) {
      console.error("Erro ao formatar a data:", error);
      return "-";
    }
  };

  const formatObservationTimestamp = (timestamp) => {
    if (!timestamp || timestamp === '' || timestamp === null || timestamp === undefined) {
      return 'Data não informada';
    }
    
    try {
      if (typeof timestamp === 'string' && timestamp.includes('/')) {
        return timestamp;
      }
      
      const date = new Date(timestamp);
      
      if (isNaN(date.getTime())) {
        console.error("Timestamp inválido:", timestamp);
        return 'Data inválida';
      }
      
      return format(date, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
    } catch (error) {
      console.error("Erro ao formatar timestamp da observação:", error, "Timestamp:", timestamp);
      return 'Erro na data';
    }
  };

  // Verificações de responsável
  const isUsuarioResponsavel = responsavelAtual === usuario?.nome;
  const temResponsavel = !!responsavelAtual;
  const podeAssumir = !temResponsavel;
  const podeLiberar = isUsuarioResponsavel;

  return (
    <div className="bg-gray-50 border border-gray-300/50 shadow-[0_8px_30px_rgba(0,0,0,0.25)] rounded-xl p-6 space-y-3">
      <h3 className="text-xl font-semibold text-gray-800">
        {titulo || `SAR #${numeroSar}` || `${acao} - ${areaTecnica}`}
      </h3>

      {/* SEÇÃO - Responsável pelo SAR */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-lg font-semibold text-blue-800">Responsável pelo SAR</h4>
          {temResponsavel && (
            <div className="flex items-center space-x-3">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${getAvatarColor(responsavelAtual)} shadow-md`}
              >
                {generateAvatar(responsavelAtual)}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-blue-800">{responsavelAtual}</span>
                <span className="text-xs text-blue-600">Responsável Atual</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex space-x-2">
          {!temResponsavel ? (
            <button
              onClick={handleAssumirSar}
              disabled={loadingAssumir}
              className="bg-blue-500 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold py-2 px-4 rounded-md text-sm flex items-center space-x-2 transition-colors duration-200 shadow-md"
            >
              {loadingAssumir ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-3.647z"/>
                  </svg>
                  <span>Assumindo...</span>
                </>
              ) : (
                <span>🙋‍♂️ Assumir SAR</span>
              )}
            </button>
          ) : isUsuarioResponsavel ? (
            <div className="flex flex-col space-y-2 w-full">
              <div className="flex items-center space-x-2 bg-green-100 border border-green-300 rounded-md p-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-800 font-medium">
                  Você é o responsável por este SAR
                </span>
              </div>
              <button
                onClick={handleLiberarSar}
                disabled={loadingAssumir}
                className="bg-orange-500 hover:bg-orange-700 disabled:bg-orange-300 text-white font-bold py-2 px-4 rounded-md text-sm flex items-center space-x-2 transition-colors duration-200 shadow-md"
              >
                {loadingAssumir ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-3.647z"/>
                    </svg>
                    <span>Liberando...</span>
                  </>
                ) : (
                  <span>🔓 Liberar SAR</span>
                )}
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2 bg-gray-100 border border-gray-300 rounded-md p-3 w-full">
              <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
              <span className="text-sm text-gray-600 italic">
                SAR assumido por <strong>{responsavelAtual}</strong>
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="text-sm text-gray-600 divide-y divide-gray-300/40">
        <p className="pb-1">
          <span className="font-medium">Número SAR:</span> {numeroSar}
        </p>
        <p className="pb-1">
          <span className="font-medium">Ação:</span> {acao || tipoServico}
        </p>
        <p className="pb-1">
          <span className="font-medium">Área Técnica:</span> {areaTecnica || tecnologia}
        </p>
        <p className="pb-1">
          <span className="font-medium">Designação:</span> {designacao}
        </p>
        <p className="pb-1">
          <span className="font-medium">Cidade:</span> {cidade}
        </p>
        <p className="pb-1">
          <span className="font-medium">Endereço NAP:</span> {endereco}
        </p>
        <p className="pb-1">
          <span className="font-medium">Quantidade Portas:</span> {quantPort || 0}
        </p>
        <p className="pb-1">
          <span className="font-medium">Caminho:</span> {caminho || descricaoServico}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data Solicitação:</span> {formatDate(dataAgendamento)}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data Vencimento:</span> {formatDate(dataVenc)}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data Execução:</span> {formatDate(horaConclusao)}
        </p>
        {dataCancelamento && (
          <p className="pb-1">
            <span className="font-medium">Data Cancelamento:</span> {formatDate(dataCancelamento)}
          </p>
        )}
        <p className="pb-1">
          <span className="font-medium">Idade Execução:</span> {idadeExecucao || 0} dias
        </p>
        {responsavelHub && (
          <p className="pb-1">
            <span className="font-medium">Responsável Hub:</span> {responsavelHub}
          </p>
        )}
        {responsavelDTC && (
          <p className="pb-1">
            <span className="font-medium">Responsável DTC:</span> {responsavelDTC}
          </p>
        )}
      </div>

      <div className="mb-2">
        <div className="flex items-center space-x-2">
          <span className="font-semibold">Status:</span>
          <select
            className="border border-gray-300 rounded-md p-2 text-sm"
            value={novoStatus}
            onChange={handleStatusChange}
          >
            <option value="Pendente">Pendente</option>
            <option value="Em Andamento">Em Execução</option>
            <option value="Concluído">Concluído</option>
            <option value="Cancelado">Cancelado</option>
          </select>
        </div>
        {confirmarStatus && (
          <div className="mt-2 flex space-x-2">
            <button
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-md text-sm transition-colors duration-200"
              onClick={handleConfirmarStatus}
            >
              Confirmar
            </button>
            <button
              className="bg-gray-300 hover:bg-gray-400 text-gray-700 font-bold py-2 px-4 rounded-md text-sm transition-colors duration-200"
              onClick={handleCancelarStatus}
            >
              Cancelar
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <span className="font-semibold">Prioridade:</span>
        <span
          className={`rounded-full px-2 py-1 text-xs font-bold ${
            prioridadeCores[prioridade] || prioridadeCores["Normal"]
          }`}
        >
          {prioridade}
        </span>
      </div>

      {/* Modal de fechamento */}
      {showModalFechamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              🏁 Finalizar SAR #{numeroSar}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Adicione uma observação de fechamento descrevendo a execução do serviço:
            </p>
            <textarea
              className="w-full border border-gray-300 rounded-md p-3 text-sm resize-none"
              rows="4"
              placeholder="Ex: Serviço executado conforme solicitado. Equipamento instalado e configurado. Cliente orientado sobre o funcionamento."
              value={observacaoFechamento}
              onChange={(e) => setObservacaoFechamento(e.target.value)}
              disabled={loadingFechamento}
            />
            <div className="flex space-x-3 mt-4">
              <button
                onClick={handleConfirmarFechamento}
                disabled={loadingFechamento}
                className="flex-1 bg-green-500 hover:bg-green-700 disabled:bg-green-300 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200"
              >
                {loadingFechamento ? (
                  <div className="flex items-center justify-center space-x-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-3.647z"/>
                    </svg>
                    <span>Finalizando...</span>
                  </div>
                ) : (
                  '✅ Finalizar SAR'
                )}
              </button>
              <button
                onClick={handleCancelarFechamento}
                disabled={loadingFechamento}
                className="flex-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-200 text-gray-700 font-bold py-2 px-4 rounded-md transition-colors duration-200"
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Seção de Observações */}
      <div className="relative z-0" ref={popoverContainerRef}>
        <button
          onClick={handleToggleObservacoes}
          className="w-full bg-claro-red hover:bg-red-700 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200 flex items-center justify-center space-x-2"
        >
          <span>
            {isObservacoesOpen
              ? "Fechar Observações"
              : "Ver/Adicionar Observações"}
          </span>
          {historicoObservacoes.length > 0 && (
            <span className="bg-white text-claro-red rounded-full px-2 py-1 text-xs font-bold">
              {historicoObservacoes.length}
            </span>
          )}
        </button>

        <div
          className={`absolute z-20 w-full bg-white border border-gray-300/50 rounded-md shadow-lg p-4
             transition-all duration-300 ease-in-out transform origin-top-left
             ${
               isObservacoesOpen
                 ? "opacity-100 scale-100 visible"
                 : "opacity-0 scale-95 invisible"
             }
             ${openAbove ? "bottom-full mb-2" : "top-full mt-2"} left-0
`}
        >
          <div className="flex items-center justify-between mb-3 border-b pb-2">
            <h4 className="text-lg font-bold">Histórico de Observações</h4>
            {historicoObservacoes.length > 0 && (
              <span className="text-xs text-gray-500">
                {historicoObservacoes.length} observação{historicoObservacoes.length !== 1 ? 'ões' : ''}
              </span>
            )}
          </div>
          
          {loadingObservacoes ? (
            <p className="text-sm text-gray-600 italic">Carregando observações...</p>
          ) : errorObservacoes ? (
            <p className="text-sm text-red-600 italic">{errorObservacoes}</p>
          ) : historicoObservacoes.length === 0 ? (
            <p className="text-sm text-gray-600 italic">
              Nenhuma observação ainda. Seja o primeiro a comentar!
            </p>
          ) : (
            <div className="space-y-3 max-h-48 overflow-y-auto pr-2">
              {historicoObservacoes
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)) // Mostrar mais recentes primeiro
                .map((obs, index) => (
                <div
                  key={index}
                  className="bg-blue-50/50 border p-3 rounded-lg"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${getAvatarColor(
                        obs.usuario
                      )}`}
                    >
                      {generateAvatar(obs.usuario)}
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-800">
                          {obs.usuario || "Usuário"}
                        </span>
                        <span className="text-xs text-blue-600">
                          {formatObservationTimestamp(obs.data || obs.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-gray-800 whitespace-pre-wrap ml-10">
                    {obs.observacao}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="mt-5 pt-4 border-t border-gray-200">
            <label
              htmlFor={`nova-observacao-${numeroSar}`}
              className="block text-gray-700 text-sm font-bold mb-2"
            >
              Adicionar Nova Observação:
            </label>
            <textarea
              id={`nova-observacao-${numeroSar}`}
              className="w-full border rounded-md p-2 text-sm resize-y"
              value={novaObservacaoTexto}
              onChange={(e) => setNovaObservacaoTexto(e.target.value)}
              rows="3"
              placeholder="Digite sua observação aqui..."
            />
            <button
              className="mt-3 w-full bg-claro-red hover:bg-red-700 text-white font-bold py-2 px-4 rounded-md text-sm transition-colors duration-200"
              onClick={handleAdicionarObservacao}
            >
              Adicionar Observação
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SarCard;