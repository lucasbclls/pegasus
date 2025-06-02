import React, { useState, useEffect, useRef } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

const ChamadoCard = ({ 
  chamado, 
  onAtualizarStatus, 
  onAtualizarResponsavel, // ← Nova prop
  onRecarregarChamados,   // ← Nova prop  
  usuario 
}) => {
  const {
    id,
    titulo,
    status: currentStatus = "Pendente",
    prioridade = "Baixa",
    responsavel, // Nova prop para o responsável atual
    dataAbertura,
    dataFechamento,
    servicoAfetado,
    causa,
    nomeSolicitante,
    telefone,
    emailSolicitante,
    empresa,
    cidade,
    tecnologia,
    nodeAfetadas,
    tipoReclamacao,
    detalhesProblema,
    testesRealizados,
    modelEquipamento,
    baseAfetada,
    contratosAfetados,
    dataEvento,
    horaInicio,
    horaConclusao,
  } = chamado;

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

  // Estados para observações
  const [historicoObservacoes, setHistoricoObservacoes] = useState([]);
  const [loadingObservacoes, setLoadingObservacoes] = useState(true);
  const [errorObservacoes, setErrorObservacoes] = useState(null);

  // NOVOS ESTADOS para assumir chamado
  const [responsavelAtual, setResponsavelAtual] = useState(responsavel);
  const [loadingAssumir, setLoadingAssumir] = useState(false);

  const popoverContainerRef = useRef(null);
  const [openAbove, setOpenAbove] = useState(false);

  // ✨ useEffect para sincronizar com as props (SÓ quando responsavel prop mudar)
  useEffect(() => {
    // Só atualiza se vier uma prop diferente do estado atual
    if (responsavel !== responsavelAtual) {
      console.log('ChamadoCard - Atualizando responsável:', {
        id: chamado.id,
        responsavelProp: responsavel,
        responsavelAtual: responsavelAtual,
        atualizando: true
      });
      setResponsavelAtual(responsavel);
    }
  }, [responsavel]); // Removido responsavelAtual da dependência para evitar loop

  // Função para carregar observações do backend
  const carregarObservacoes = async () => {
    setLoadingObservacoes(true);
    setErrorObservacoes(null);
    try {
      const response = await fetch(`http://localhost:5000/chamados/${id}/observacoes`);
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
    // Remove notificações existentes
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(notification => notification.remove());

    // Cria nova notificação
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

    // Anima a entrada
    setTimeout(() => {
      notification.classList.remove('translate-x-full');
    }, 100);

    // Remove após 3 segundos
    setTimeout(() => {
      notification.classList.add('translate-x-full');
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, 3000);
  };

  // ✅ FUNÇÃO ATUALIZADA para assumir o chamado com apenas_visual
  const handleAssumirChamado = async () => {
    // ✅ Verificação adicional antes de tentar assumir
    if (temResponsavel) {
      mostrarNotificacao(`Este chamado já foi assumido por ${responsavelAtual}`, 'error');
      return;
    }

    setLoadingAssumir(true);
    const usuarioLogado = JSON.parse(localStorage.getItem('usuario')) || { nome: 'Usuário' };

    try {
      const response = await fetch(`http://localhost:5000/chamados/${id}/assumir`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          responsavel: usuarioLogado.nome,
          apenas_visual: true // ✅ NOVO: Parâmetro para evitar erros Excel/Redmine
        }),
      });

      const data = await response.json();
      console.log('🔄 RESPOSTA DA API:', data);

      if (response.ok && data.success) {
        // ✅ Atualizar estado local imediatamente com o nome do usuário
        const nomeUsuario = data.responsavel_nome || usuarioLogado.nome;
        
        console.log('✅ Assumindo chamado - Estado antes:', responsavelAtual);
        setResponsavelAtual(nomeUsuario);
        console.log('✅ Assumindo chamado - Estado depois:', nomeUsuario);
        
        // ✅ Use a nova função específica para responsável se disponível
        if (onAtualizarResponsavel) {
          console.log('✅ Chamando onAtualizarResponsavel');
          onAtualizarResponsavel(id, nomeUsuario);
        }
        // ✅ Fallback para a função original (compatibilidade)
        else if (onAtualizarStatus) {
          console.log('✅ Chamando onAtualizarStatus');
          await onAtualizarStatus(id, currentStatus, historicoObservacoes, nomeUsuario);
        }
        
        // ✅ Notificação visual moderna com nome do usuário
        mostrarNotificacao(`✅ Chamado assumido por ${nomeUsuario}!`, 'success');
        
        console.log(`✅ Chamado ${id} assumido por ${nomeUsuario} (apenas visual: ${data.apenas_visual})`);
      } else if (response.status === 409) {
        // ✅ Chamado já foi assumido por outro usuário
        mostrarNotificacao('❌ Este chamado já foi assumido por outro usuário!', 'error');
        // Força sincronização para atualizar interface
        if (onRecarregarChamados) {
          onRecarregarChamados();
        }
      } else {
        throw new Error(data.erro || "Erro ao assumir o chamado");
      }
    } catch (error) {
      console.error("Erro ao assumir chamado:", error);
      mostrarNotificacao(`Erro ao assumir chamado: ${error.message}`, 'error');
    } finally {
      setLoadingAssumir(false);
    }
  };

  // ✅ FUNÇÃO ATUALIZADA para liberar o chamado
  const handleLiberarChamado = async () => {
    setLoadingAssumir(true);
    try {
      const response = await fetch(`http://localhost:5000/chamados/${id}/liberar`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          apenas_visual: true // ✅ NOVO: Consistência com assumir
        }),
      });

      const data = await response.json();
      console.log('🔄 RESPOSTA DA API LIBERAR:', data);

      if (response.ok && data.success) {
        // ✅ Atualizar estado local imediatamente
        console.log('✅ LIBERANDO CHAMADO - Estado antes:', responsavelAtual);
        setResponsavelAtual(null);
        console.log('✅ LIBERANDO CHAMADO - Estado depois: null');
        
        // ✅ Use a nova função específica para responsável se disponível
        if (onAtualizarResponsavel) {
          console.log('✅ Chamando onAtualizarResponsavel com null');
          onAtualizarResponsavel(id, null);
        }
        // ✅ Fallback para a função original (compatibilidade)
        else if (onAtualizarStatus) {
          console.log('✅ Chamando onAtualizarStatus com null');
          await onAtualizarStatus(id, currentStatus, historicoObservacoes, null);
        }
        
        // ✅ Notificação visual moderna ao invés de alert
        mostrarNotificacao("Chamado liberado com sucesso!", 'success');
        
        console.log(`✅ Chamado ${id} liberado (apenas visual: ${data.apenas_visual})`);
      } else {
        throw new Error(data.erro || "Erro ao liberar o chamado");
      }
    } catch (error) {
      console.error("Erro ao liberar chamado:", error);
      mostrarNotificacao(`Erro ao liberar chamado: ${error.message}`, 'error');
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
    setNovoStatus(event.target.value);
    setConfirmarStatus(true);
  };

  const handleConfirmarStatus = async () => {
    try {
      let url = "";
      let payload = {};

      if (novoStatus === "Concluído") {
        url = `http://localhost:5000/chamados/${id}/finalizar`;
      } else if (novoStatus === "Cancelado") {
        url = `http://localhost:5000/chamados/${id}/cancelar`;
      } else {
        url = `http://localhost:5000/chamados/${id}`;
        payload = { status: novoStatus };
      }

      const response = await fetch(url, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: Object.keys(payload).length > 0 ? JSON.stringify(payload) : null,
      });

      if (response.ok) {
        setConfirmarStatus(false);
        onAtualizarStatus?.(id, novoStatus, historicoObservacoes, responsavelAtual);
        mostrarNotificacao(`Status atualizado para: ${novoStatus}`, 'success');
      } else {
        throw new Error("Erro ao atualizar o status do chamado.");
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
      // Carrega observações quando abre pela primeira vez
      if (newState && historicoObservacoes.length === 0) {
        carregarObservacoes();
      }
      return newState;
    });
  };

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
        `http://localhost:5000/chamados/${id}/observacao`,
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

  // Verificar se o usuário atual é o responsável
  const isUsuarioResponsavel = responsavelAtual === usuario?.nome;
  const temResponsavel = !!responsavelAtual;
  const podeAssumir = !temResponsavel; // ✅ Só pode assumir se não tem responsável
  const podeLiberar = isUsuarioResponsavel; // ✅ Só pode liberar se for o responsável atual

  return (
    <div className="bg-gray-50 border border-gray-300/50 shadow-[0_8px_30px_rgba(0,0,0,0.25)] rounded-xl p-6 space-y-3">
      <h3 className="text-xl font-semibold text-gray-800">
        {titulo || servicoAfetado || `Chamado #${id}`}
      </h3>

        {/* SEÇÃO - Responsável pelo Chamado */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-blue-800">Responsável pelo Chamado</h4>
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
                onClick={handleAssumirChamado}
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
                  <span>🙋‍♂️ Assumir Chamado</span>
                )}
              </button>
            ) : isUsuarioResponsavel ? (
              <div className="flex flex-col space-y-2 w-full">
                <div className="flex items-center space-x-2 bg-green-100 border border-green-300 rounded-md p-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-green-800 font-medium">
                    Você é o responsável por este chamado
                  </span>
                </div>
                <button
                  onClick={handleLiberarChamado}
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
                    <span>🔓 Liberar Chamado</span>
                  )}
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2 bg-gray-100 border border-gray-300 rounded-md p-3 w-full">
                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                <span className="text-sm text-gray-600 italic">
                  Chamado assumido por <strong>{responsavelAtual}</strong>
                </span>
              </div>
            )}
          </div>
        </div>

      <div className="text-sm text-gray-600 divide-y divide-gray-300/40">
        <p className="pb-1">
          <span className="font-medium">ID:</span> {id}
        </p>
        <p className="pb-1">
          <span className="font-medium">Data do Evento:</span> {dataEvento}
        </p>
        <p className="pb-1">
          <span className="font-medium">Hora do Inicio:</span> {horaInicio}
        </p>
        <p className="pb-1">
          <span className="font-medium">Nome Solicitante:</span>{" "}
          {nomeSolicitante}
        </p>
        <p className="pb-1">
          <span className="font-medium">Email Solicitante:</span>{" "}
          {emailSolicitante}
        </p>
        <p className="pb-1">
          <span className="font-medium">Empresa:</span> {empresa}
        </p>
        <p className="pb-1">
          <span className="font-medium">Cidade:</span> {cidade}
        </p>
        <p className="pb-1">
          <span className="font-medium">Tecnologia:</span> {tecnologia}
        </p>
        <p className="pb-1">
          <span className="font-medium">Nodes Afetadas:</span> {nodeAfetadas}
        </p>
        <p className="pb-1">
          <span className="font-medium">Detalhes Problema:</span>{" "}
          {detalhesProblema}
        </p>
        <p className="pb-1">
          <span className="font-medium">Testes Realizado:</span>{" "}
          {testesRealizados}
        </p>
        <p className="pb-1">
          <span className="font-medium">Modelo do Equipamento:</span>{" "}
          {modelEquipamento}
        </p>
        <p className="pb-1">
          <span className="font-medium">Base Afetada:</span> {baseAfetada}
        </p>
        <p className="pb-1">
          <span className="font-medium">Contratos Afetados:</span>{" "}
          {contratosAfetados}
        </p>
        <p className="pb-1">
          <span className="font-medium">Serviço Afetado:</span> {servicoAfetado}
        </p>
        <p className="pb-1">
          <span className="font-medium">Hora da Conclusão:</span>{" "}
          {horaConclusao}
        </p>
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
            <option value="Em Andamento">Em Atendimento</option>
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
            prioridadeCores[prioridade] || prioridadeCores["Baixa"]
          }`}
        >
          {prioridade}
        </span>
      </div>

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
              htmlFor={`nova-observacao-${id}`}
              className="block text-gray-700 text-sm font-bold mb-2"
            >
              Adicionar Nova Observação:
            </label>
            <textarea
              id={`nova-observacao-${id}`}
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

export default ChamadoCard;