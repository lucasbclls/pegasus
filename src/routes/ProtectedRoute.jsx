import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Importe seu hook de autenticação

const ProtectedRoute = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    // Pode renderizar um spinner ou uma tela de carregamento aqui
    return <div className="flex justify-center items-center h-screen text-lg">Carregando...</div>;
  }

  // Se não estiver autenticado, redireciona para a página de login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Se estiver autenticado, renderiza os componentes filhos da rota
  return <Outlet />;
};

export default ProtectedRoute;