import React from 'react';
import { Link } from 'react-router-dom';
import {
  User,
  Settings,
  Bell,
  ClipboardList,
  LogOut,
  LayoutDashboard,
  HelpCircle,
  Info,
  Wrench
} from 'lucide-react';

const Sidebar = ({ isOpen, onMouseEnter, onMouseLeave, onSetSidebarOpen }) => {
  const handleLogout = () => {
    // Lógica de logout
    console.log('Logout executado');
  };

  return (
    <aside
      className={`
        bg-white text-gray-800 w-64 p-4 fixed h-full z-20 top-0 left-0
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        ${isOpen ? 'block' : 'hidden'} lg:block
        shadow-lg
      `}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="flex items-center gap-3 mb-6">
        <img src="/emojis/emoji1.png" alt="avatar" className="w-10 h-10 rounded-full" />
        <div>
          <p className="text-sm font-semibold">Olá, João</p>
          <p className="text-xs text-gray-500">Administrador</p>
        </div>
      </div>

      <h2 className="text-xl font-bold mb-6 text-center">Menu</h2>

      <nav className="space-y-2">
        <Link
          to="/dashboard"
          className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 transition duration-150 ease-in-out"
          onClick={() => onSetSidebarOpen(false)}
        >
          <LayoutDashboard size={18} /> Painel
        </Link>
<hr className="my-4 border-gray-300" />
        <Link
          to="/gerenciamento"
          className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 transition duration-150 ease-in-out"
          onClick={() => onSetSidebarOpen(false)}
        >
          <ClipboardList size={18} /> Gerenciamento de Chamados
        </Link>

        <Link
          to="/execucao-sar"
          className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 transition duration-150 ease-in-out"
          onClick={() => onSetSidebarOpen(false)}
        >
          <Wrench size={18} /> Execução de Sar
        </Link>

        

      </nav>

      <div className="absolute bottom-4 left-4 right-4">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 text-red-600 hover:bg-red-50 py-2 px-3 rounded transition"
        >
          <LogOut size={18} /> Sair
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;