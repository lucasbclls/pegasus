import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Header = ({ onToggleSidebar }) => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // A função handleRegistrarNovoChamado foi removida
  // A variável shouldShowRegisterButton foi removida

  // As rotas públicas ainda são úteis para outras lógicas, se houver,
  // mas não são mais diretamente usadas para o botão 'Novo Chamado'.
  // Se não precisar delas para mais nada no Header, pode removê-las também.
  const publicRoutes = ['/login', '/register', '/']; 

  return (
    <header className="bg-claro-red p-4 flex items-center justify-between shadow-md z-30 relative">
      <div className="flex items-center">
        {isAuthenticated && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="text-white focus:outline-none mr-4 lg:inline-flex"
          >
            {/* ícone das 3 linhas */}
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        )}
        <h1 className="text-white text-2xl font-bold">Sistema de Chamados</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* O bloco do botão 'Novo Chamado' foi removido daqui */}
      </div>
    </header>
  );
};

export default Header;