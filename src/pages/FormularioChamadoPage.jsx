import React, { useState } from 'react';
import FormularioChamado from '../components/FormularioChamado';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import Footer from '../components/Footer';
import { useNavigate } from 'react-router-dom';

const FormularioChamadoPage = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleAdicionarNovoChamado = (novoChamado) => {
    console.log('Novo chamado a ser adicionado:', novoChamado);
    navigate('/');
  };

  const openSidebar = () => {
    setSidebarOpen(true);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header onToggleSidebar={toggleSidebar} /> 
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={sidebarOpen} onMouseEnter={openSidebar} onMouseLeave={closeSidebar} />
        
        <main className={`flex-1 p-4 bg-gray-100 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
          {/* Adicione um contêiner com largura máxima e centralização */}
          <div className="max-w-3xl mx-auto py-8"> {/* max-w-3xl, mx-auto e py-8 */}
            <h2 className="text-xl font-semibold mb-4 text-text-gray text-center">Novo Chamado</h2> {/* Centralize o título também */}
            <div className="bg-white p-6 rounded shadow-md"> {/* Aumentei o padding para p-6 */}
              <FormularioChamado onAdicionar={handleAdicionarNovoChamado} />
            </div>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default FormularioChamadoPage;