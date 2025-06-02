import React, { useState } from "react";

const FormularioChamado = ({ onAdicionar }) => {
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [prioridade, setPrioridade] = useState("Média");

  const handleSubmit = (event) => {
    event.preventDefault();
    if (titulo.trim()) {
      onAdicionar({ titulo, descricao, prioridade, status: "Pendente" });
      setTitulo("");
      setDescricao("");
      setPrioridade("Média");
    } else {
      alert("O título do chamado é obrigatório.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="titulo"
          className="block text-gray-700 text-sm font-bold mb-2"
        >
          Título:
        </label>
        <input
          type="text"
          id="titulo"
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
        />
      </div>
      <div>
        <label
          htmlFor="descricao"
          className="block text-gray-700 text-sm font-bold mb-2"
        >
          Descrição:
        </label>
        <textarea
          id="descricao"
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
        />
      </div>
      <div>
        <label
          htmlFor="prioridade"
          className="block text-gray-700 text-sm font-bold mb-2"
        >
          Prioridade:
        </label>
        <select
          id="prioridade"
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          value={prioridade}
          onChange={(e) => setPrioridade(e.target.value)}
        >
          <option value="Baixa">Baixa</option>
          <option value="Média">Média</option>
          <option value="Alta">Alta</option>
        </select>
      </div>
      <button
        type="submit"
        className="bg-claro-red hover:bg-claro-red-dark text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
      >
        Adicionar Chamado
      </button>
    </form>
  );
};

export default FormularioChamado;
