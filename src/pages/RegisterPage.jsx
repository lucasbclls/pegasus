import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const avatarOptions = [
  '/fibra.svg',
  '/dtc.svg',
  '/claro.svg',
];


const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState(avatarOptions[0]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

const handleSubmit = async (e) => {
  e.preventDefault();
  setError('');
  setSuccess('');

  if (password !== confirmPassword) {
    setError('As senhas não coincidem.');
    return;
  }

  try {
    const response = await fetch('http://localhost:5003/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email,
        usuario: username,
        senha: password,
        confirmar_senha: confirmPassword,
        avatar: selectedAvatar,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Erro no registro');
    }

    setSuccess(data.message || 'Cadastro realizado com sucesso!');
    setTimeout(() => navigate('/login'), 2000);
  } catch (err) {
    setError(err.message);
  }
};


  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-3xl font-bold text-center text-claro-red mb-6">Cadastro</h2>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4">
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4">
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Avatar Picker */}
          <div>
            <label className="block text-gray-700 text-sm font-bold mb-2 text-center">
              Escolha seu avatar
            </label>
            <div className="flex flex-wrap gap-3 justify-center">
              {avatarOptions.map((avatarUrl, index) => (
                <img
                  key={index}
                  src={avatarUrl}
                  alt={`Avatar ${index + 1}`}
                  className={`w-14 h-14 rounded-full cursor-pointer border-4 transition duration-200 ${
                    selectedAvatar === avatarUrl
                      ? 'border-blue-500 scale-105'
                      : 'border-transparent hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedAvatar(avatarUrl)}
                />
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-gray-700 text-sm font-bold mb-2">
              Email:
            </label>
            <input
              type="email"
              id="email"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="seuemail@claro.com.br"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label htmlFor="username" className="block text-gray-700 text-sm font-bold mb-2">
              Usuário:
            </label>
            <input
              type="text"
              id="username"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="Escolha um nome de usuário"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
              Senha:
            </label>
            <input
              type="password"
              id="password"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-gray-700 text-sm font-bold mb-2">
              Confirmar Senha:
            </label>
            <input
              type="password"
              id="confirmPassword"
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-claro-red hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition duration-200 ease-in-out"
          >
            Cadastrar
          </button>
        </form>

        <p className="text-center text-gray-600 text-sm mt-6">
          Já tem uma conta?{' '}
          <Link to="/login" className="text-blue-500 hover:text-blue-700 font-bold">
            Faça login aqui
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
