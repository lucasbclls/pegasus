import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

const handleSubmit = async (e) => {
  e.preventDefault();
  setError('');

  try {
    const response = await fetch('http://localhost:5004/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, senha }),
    });

    const data = await response.json();

    if (response.ok) {
      // 👉 Salva o usuário no AuthContext
      login(data.usuario); // Ex: { nome: "João", email: "...", avatar: null }

      // 👉 Também salva no localStorage, se quiser usar em outras partes sem contexto
      localStorage.setItem("usuario", JSON.stringify(data.usuario));

      navigate('/gerenciamento');
    } else {
      setError(data.message || 'Erro ao fazer login.');
    }
  } catch (err) {
    setError('Erro de conexão com o servidor.');
    console.error(err);
  }
};


  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-3xl font-bold text-center text-claro-red mb-6">Login</h2>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="block text-gray-700 text-sm font-bold mb-2">
              Email:
            </label>
            <input
              type="email"
              id="email"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="Digite seu email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="senha" className="block text-gray-700 text-sm font-bold mb-2">
              Senha:
            </label>
            <input
              type="password"
              id="senha"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="••••••••"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="w-full bg-claro-red hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition duration-200 ease-in-out"
          >
            Entrar
          </button>
        </form>
        <p className="text-center text-gray-600 text-sm mt-6">
          Não tem uma conta?{' '}
          <Link to="/register" className="text-blue-500 hover:text-blue-700 font-bold">
            Cadastre-se aqui
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
