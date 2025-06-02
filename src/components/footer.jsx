import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-200 py-3 text-center text-gray-600 text-sm">
      &copy; {new Date().getFullYear()} Paulo Lucas Barcellos/Claro S.A - Todos os direitos reservados.
    </footer>
  );
};

export default Footer;