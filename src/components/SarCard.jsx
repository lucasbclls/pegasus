import React, { useState, useEffect, useRef } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

const SarCard = ({ 
  sar, 
  onAtualizarStatus, 
  onAtualizarResponsavel, 
  onRecarregarSars,   
  usuario 
}) => {
  const {
    id, // Este será o NumSar
    numeroSar,
    status: currentStatus = "Pendente",
    prioridade = "Normal",
    responsavel,
    responsavelDTC,
    dataSolicitacao,
    cidade,
    acao,
    areaTecnica,
    designacao,
    enderecoNap,
    quantPort,
    caminho,
    responsavelHub,
    dataVenc,
    dataExecucao,
    dataCancelamento,
    idadeExecucao,
    anoMes,
    idRedmine,
    // Campos de compatibilidade
    tipoServico,
    cliente,
    endereco,
    tecnologia,
    descricaoServico,
    observacoes,
  } = sar;

  // Usar NumSar como identificador principal
  const sarIdentifier = numeroSar || id;
  const responsavelAtualReal = responsavelDTC || responsavel;

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
  const [responsavelAtual, setResponsavelAtual] = useState(responsavelAtualReal);
  const [loadingAssumir, setLoadingAssumir] = useState(false);

  const popoverContainerRef = useRef(null);
  const [openAbove, setOpenAbove] = useState(false);

  // useEffect para sincronizar com as props
  useEffect(() => {
    if (responsavelAtualReal !== responsavelAtual) {
      console.log('SarCard - Atualizando responsável:', {
        sarId: sarIdentifier,
        responsavelProp: responsavelAtualReal,
        responsavelAtual: responsavelAtual,
        atualizando: true
      });
      setResponsavelAtual(responsavelAtualReal);
    }
  }, [responsavelAtualReal]);

  // ✅ ALTERADO: Função para carregar observações do backend - PORTA 5007
  const carregarObservacoes = async () => {
    setLoadingObservacoes(true);
    setErrorObservacoes(null);
    try {
      const response = await fetch(`http://localhost:5007/sars/${sarIdentifier}/observacoes`);
      if (!response.ok) {
        throw new Error(`Erro ao carregar observações: ${response.statusText}`);
      }
      const data = await response.json();
      if (Array.isArray(data.observacoes)) {
        const observacoesOrdenadas = data.observacoes.sort((a, b) => {
          const dateA = new Date(a.timestamp || 0).getTime();
          const dateB = new Date(b.timestamp || 0).getTime();
          return dateA - dateB;
        });
        setHistoricoObservacoes(observacoesOrdenadas);
      } else {
        setHistoricoObservacoes([]);
      }
    } catch (err) {
      console.error("Falha ao carregar observações:", err);
      setErrorObservacoes("Não foi possível carregar as observações.");
    } finally {
      setLoadingObservacoes(false);
    }
  };

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

  // ✅ ALTERADO: Função para assumir o SAR - PORTA 5007
  const handleAssumirSar = async () => {
    if (temResponsavel) {
      mostrarNotificacao(`Este SAR já foi assumido por ${responsavelAtual}`, 'error');
      return;
    }

    setLoadingAssumir(true);
    const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário' };

    try {
      const response = await fetch(`http://localhost:5007/sars/${sarIdentifier}/assumir`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          responsavel: usuarioLogado.nome,
          apenas_visual: true
        }),
      });

      const data = await response.json();
      console.log('🔄 RESPOSTA DA API SAR:', data);

      if (response.ok && data.success) {
        const nomeUsuario = data.responsavel_nome || usuarioLogado.nome;
        
        console.log('✅ Assumindo SAR - Estado antes:', responsavelAtual);
        setResponsavelAtual(nomeUsuario);
        console.log('✅ Assumindo SAR - Estado depois:', nomeUsuario);
        
        if (onAtualizarResponsavel) {
          console.log('✅ Chamando onAtualizarResponsavel');
          onAtualizarResponsavel(sarIdentifier, nomeUsuario);
        }
        else if (onAtualizarStatus) {
          console.log('✅ Chamando onAtualizarStatus');
          await onAtualizarStatus(sarIdentifier, currentStatus, historicoObservacoes, nomeUsuario);
        }
        
        mostrarNotificacao(`✅ SAR assumido por ${nomeUsuario}!`, 'success');
        
        console.log(`✅ SAR ${sarIdentifier} assumido por ${nomeUsuario} (apenas visual: ${data.apenas_visual})`);
      } else if (response.status === 409) {
        mostrarNotificacao('❌ Este SAR já foi assumido por outro usuário!', 'error');
        if (onRecarregarSars) {
          onRecarregarSars();
        }
      } else {
        throw new Error(data.erro || "Erro ao assumir o SAR");
      }
    } catch (error) {
      console.error("Erro ao assumir SAR:", error);
      mostrarNotificacao(`Erro ao assumir SAR: ${error.message}`, 'error');
    } finally {
      setLoadingAssumir(false);
    }
  };

  // ✅ ALTERADO: Função para liberar o SAR - PORTA 5007
  const handleLiberarSar = async () => {
    setLoadingAssumir(true);
    try {
      const response = await fetch(`http://localhost:5007/sars/${sarIdentifier}/liberar`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          apenas_visual: true
        }),
      });

      const data = await response.json();
      console.log('🔄 RESPOSTA DA API LIBERAR SAR:', data);

      if (response.ok && data.success) {
        console.log('✅ LIBERANDO SAR - Estado antes:', responsavelAtual);
        setResponsavelAtual(null);
        console.log('✅ LIBERANDO SAR - Estado depois: null');
        
        if (onAtualizarResponsavel) {
          console.log('✅ Chamando onAtualizarResponsavel com null');
          onAtualizarResponsavel(sarIdentifier, null);
        }
        else if (onAtualizarStatus) {
          console.log('✅ Chamando onAtualizarStatus com null');
          await onAtualizarStatus(sarIdentifier, currentStatus, historicoObservacoes, null);
        }
        
        mostrarNotificacao("SAR liberado com sucesso!", 'success');
        
        console.log(`✅ SAR ${sarIdentifier} liberado (apenas visual: ${data.apenas_visual})`);
      } else {
        throw new Error(data.erro || "Erro ao liberar o SAR");
      }
    } catch (error) {
      console.error("Erro ao liberar SAR:", error);
      mostrarNotificacao(`Erro ao liberar SAR: ${error.message}`, 'error');
    } finally {
      setLoadingAssumir(false);
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

  const handleStatusChange = (event) => {
    const novoStatusSelecionado = event.target.value;
    setNovoStatus(novoStatusSelecionado);
    
    if (novoStatusSelecionado === "Concluído") {
      setShowModalFechamento(true);
    } else {
      setConfirmarStatus(true);
    }
  };

  // ✅ ALTERADO: Função para processar o fechamento com observação - PORTA 5007
  const handleConfirmarFechamento = async () => {
    if (observacaoFechamento.trim() === "") {
      mostrarNotificacao("Por favor, adicione uma observação de fechamento.", 'error');
      return;
    }

    setLoadingFechamento(true);
    try {
      // 1️⃣ PRIMEIRO: Adicionar a observação de fechamento
      const observacaoPayload = {
        observacao: `[FECHAMENTO] ${observacaoFechamento.trim()}`,
        usuario: usuario?.nome || "Sistema",
      };

      const observacaoResponse = await fetch(
        `http://localhost:5007/sars/${sarIdentifier}/observacao`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(observacaoPayload),
        }
      );

      if (!observacaoResponse.ok) {
        throw new Error("Erro ao adicionar observação de fechamento");
      }

      // 2️⃣ SEGUNDO: Finalizar o SAR
      const finalizarResponse = await fetch(`http://localhost:5007/sars/${sarIdentifier}/finalizar`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (finalizarResponse.ok) {
        setShowModalFechamento(false);
        setObservacaoFechamento("");
        onAtualizarStatus?.(sarIdentifier, "Concluído", historicoObservacoes, responsavelAtual);
        mostrarNotificacao("SAR finalizado com sucesso!", 'success');
      } else {
        throw new Error("Erro ao finalizar o SAR.");
      }
    } catch (error) {
      console.error(error);
      mostrarNotificacao(`Erro: ${error.message}`, 'error');
    } finally {
      setLoadingFechamento(false);
    }
  };

  const handleCancelarFechamento = () => {
    setShowModalFechamento(false);
    setObservacaoFechamento("");
    setNovoStatus(currentStatus);
  };

  // ✅ ALTERADO: Função para confirmar status - PORTA 5007
  const handleConfirmarStatus = async () => {
    try {
      const url = `http://localhost:5007/api/sars/${sarIdentifier}`;
      const payload = { status: novoStatus };

      const response = await fetch(url, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setConfirmarStatus(false);
        onAtualizarStatus?.(sarIdentifier, novoStatus, historicoObservacoes, responsavelAtual);
        mostrarNotificacao(`Status atualizado para: ${novoStatus}`, 'success');
      } else {
        throw new Error("Erro ao atualizar o status do SAR.");
      }
    } catch (error) {
      console.error(error);
      mostrarNotificacao("Erro ao atualizar status", 'error');
    }
  };

  const handleCancelarStatus = () => {
    setNovoStatus(currentStatus);
    setConfirmarStatus(false);
  };

  const handleToggleObservacoes = () => {
    setIsObservacoesOpen((prev) => {
      const newState = !prev;
      if (newState && historicoObservacoes.length === 0) {
        carregarObservacoes();
      }
      return newState;
    });
  };

  // ✅ ALTERADO: Função para adicionar observação - PORTA 5007
  const handleAdicionarObservacao = async () => {
    if (novaObservacaoTexto.trim() === "") {
      mostrarNotificacao("Por favor, digite uma observação.", 'error');
      return;
    }

    try {
      const payload = {
        observacao: novaObservacaoTexto.trim(),
        usuario: usuario?.nome || "Usuário Anônimo",
      };

      const response = await fetch(
        `http://localhost:5007/sars/${sarIdentifier}/observacao`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();
      if (response.ok) {
        await carregarObservacoes();
        setNovaObservacaoTexto("");
        mostrarNotificacao("Observação adicionada com sucesso!", 'success');
      } else {
        throw new Error(data.erro || "Erro ao adicionar observação");
      }
    } catch (error) {
      console.error(error);
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

  const formatDateOnly = (dateString) => {
    if (!dateString) return "-";
    try {
      const date = new Date(dateString);
      return format(date, "dd/MM/yyyy", { locale: ptBR });
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
        SAR #{numeroSar || sarIdentifier}
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
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-3.647z"/>
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
          <span className="font-medium">Número SAR:</span> {numeroSar || sarIdentifier}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data Solicitação:</span> {formatDate(dataSolicitacao)}
        </p>
        <p className="pb-1">
          <span className="font-medium">Cidade:</span> {cidade}
        </p>
        <p className="pb-1">
          <span className="font-medium">Ação:</span> {acao || tipoServico}
        </p>
        <p className="pb-1">
          <span className="font-medium">Área Técnica:</span> {areaTecnica || tecnologia}
        </p>
        <p className="pb-1">
          <span className="font-medium">Designação:</span> {designacao || cliente}
        </p>
        <p className="pb-1">
          <span className="font-medium">Endereço NAP:</span> {enderecoNap || endereco}
        </p>
        <p className="pb-1">
          <span className="font-medium">Quantidade Portas:</span> {quantPort || '-'}
        </p>
        <p className="pb-1">
          <span className="font-medium">Responsável Hub:</span> {responsavelHub}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data Vencimento:</span> {formatDateOnly(dataVenc)}
        </p>
        {dataExecucao && (
          <p className="pb-1">
            <span className="font-medium">Data Execução:</span> {formatDate(dataExecucao)}
          </p>
        )}
        {dataCancelamento && (
          <p className="pb-1">
            <span className="font-medium">Data Cancelamento:</span> {formatDate(dataCancelamento)}
          </p>
        )}
        {idadeExecucao && (
          <p className="pb-1">
            <span className="font-medium">Idade Execução (dias):</span> {idadeExecucao}
          </p>
        )}
        {idRedmine && idRedmine > 0 && (
          <p className="pb-1">
            <span className="font-medium">ID Redmine:</span> {idRedmine}
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
              🏁 Finalizar SAR #{numeroSar || sarIdentifier}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Adicione uma observação de fechamento descrevendo a execução do serviço:
            </p>
            <textarea
              className="w-full border border-gray-300 rounded-md p-3 text-sm resize-none"
              rows="4"
              placeholder="Ex: Serviço executado conforme solicitado. Instalação realizada com sucesso. Cliente orientado sobre o procedimento."
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
          className="w-full bg-claro-red hover:bg-red-700 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200"
        >
          {isObservacoesOpen
            ? "Fechar Observações"
            : "Ver/Adicionar Observações"}
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
          <h4 className="text-lg font-bold mb-3 border-b pb-2">
            Histórico de Observações
          </h4>
          {loadingObservacoes ? (
            <p className="text-sm text-gray-600 italic">Carregando observações...</p>
          ) : errorObservacoes ? (
            <p className="text-sm text-red-600 italic">{errorObservacoes}</p>
          ) : historicoObservacoes.length === 0 ? (
            <p className="text-sm text-gray-600 italic">
              Nenhuma observação ainda.
            </p>
          ) : (
            <div className="space-y-3 max-h-48 overflow-y-auto pr-2">
              {historicoObservacoes.map((obs, index) => (
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
              htmlFor={`nova-observacao-${sarIdentifier}`}
              className="block text-gray-700 text-sm font-bold mb-2"
            >
              Adicionar Nova Observação:
            </label>
            <textarea
              id={`nova-observacao-${sarIdentifier}`}
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