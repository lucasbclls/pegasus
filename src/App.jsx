
// src/App.jsx
import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';

import GerenciamentoChamados from './pages/GerenciamentoChamados';
import ExecucaoSar from './pages/ExecucaoSar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import FormularioChamadoPage from './pages/FormularioChamadoPage';

import ProtectedRoute from './routes/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';

import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Footer from './components/Footer';

// Layout para páginas públicas
function PublicLayout() {
  return (
    <>
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}

// Layout para páginas protegidas com sidebar, header e footer
function ProtectedLayout({
  sidebarOpen,
  handleToggleSidebar,
  handleMouseEnterSidebar,
  handleMouseLeaveSidebar,
  setSidebarOpen,
}) {
  return (
    <>
      <Header onToggleSidebar={handleToggleSidebar} />
      <div className="flex">
        {/* Sidebar sempre visível */}
        <Sidebar
          isOpen={sidebarOpen}
          onMouseEnter={handleMouseEnterSidebar}
          onMouseLeave={handleMouseLeaveSidebar}
          onSetSidebarOpen={setSidebarOpen}
        />
        <main className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
          <Outlet />
          <Footer />
        </main>
      </div>
    </>
  );
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const handleToggleSidebar = () => setSidebarOpen(!sidebarOpen);
  const handleMouseEnterSidebar = () => setSidebarOpen(true);
  const handleMouseLeaveSidebar = () => setSidebarOpen(false);

  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Layout público: login e registro */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Layout protegido com sidebar, header e footer */}
          <Route
            element={
              <ProtectedRoute>
                <ProtectedLayout
                  sidebarOpen={sidebarOpen}
                  handleToggleSidebar={handleToggleSidebar}
                  handleMouseEnterSidebar={handleMouseEnterSidebar}
                  handleMouseLeaveSidebar={handleMouseLeaveSidebar}
                  setSidebarOpen={setSidebarOpen}
                />
              </ProtectedRoute>
            }
          >
            <Route path="/gerenciamento" element={<GerenciamentoChamados />} />
            <Route path="/execucao-sar" element={<ExecucaoSar />} />
            <Route path="/novo-chamado" element={<FormularioChamadoPage />} />
          </Route>

          {/* Redireciona qualquer outra rota para login */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;