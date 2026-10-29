import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { SearchModal } from './SearchModal';
import { NotificationsModal } from './NotificationsModal';
import { useApp } from '../../context/AppContext';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const { themeMode } = useApp();

  // Dynamic subtle background styling according to active theme
  const getBackgroundGradient = () => {
    switch (themeMode) {
      case 'flood':
        return 'bg-gradient-to-br from-[#06141F] via-[#081F30] to-[#040D15]';
      case 'drought':
        return 'bg-gradient-to-br from-[#120C07] via-[#1B140B] to-[#070503]';
      case 'overview':
      default:
        return 'bg-gradient-to-br from-[#06141D] via-[#091D2B] to-[#040B10]';
    }
  };

  return (
    <div className={`min-h-screen text-slate-100 flex flex-col font-sans transition-colors duration-500 ${getBackgroundGradient()}`}>
      {/* Sidebar for desktop and drawer for mobile */}
      <Sidebar />

      {/* Main Content Area (offset by 64 / 16rem on desktop) */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen transition-all">
        <Header />

        <main className="flex-1 p-4 lg:p-7 max-w-[1600px] w-full mx-auto animate-fadeIn">
          {children}
        </main>
      </div>

      {/* Global Interactive Overlays */}
      <SearchModal />
      <NotificationsModal />
    </div>
  );
};
