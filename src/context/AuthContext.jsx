import React, { createContext, useState, useContext, useEffect } from 'react';

// Cria o contexto de autenticação
const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // Estado para armazenar o token do usuário (simula o login)
  const [authToken, setAuthToken] = useState(localStorage.getItem('authToken'));
  const [isLoading, setIsLoading] = useState(true); // Para indicar se a verificação inicial está completa

  // Verifica o token no localStorage ao carregar a aplicação
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      setAuthToken(token);
    }
    setIsLoading(false); // Carregamento inicial concluído
  }, []);

  const login = (token) => {
    setAuthToken(token);
    localStorage.setItem('authToken', token); // Armazena o token para persistência
  };

  const logout = () => {
    setAuthToken(null);
    localStorage.removeItem('authToken'); // Remove o token do localStorage
  };

  // Determina se o usuário está logado
  const isAuthenticated = !!authToken; // true se authToken não for null/undefined

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook customizado para usar o contexto de autenticação
export const useAuth = () => {
  return useContext(AuthContext);
};