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

  // Clean, high-legibility light institutional background
  const getBackgroundGradient = () => {
    switch (themeMode) {
      case 'flood':
        return 'bg-slate-50';
      case 'drought':
        return 'bg-slate-50';
      case 'overview':
      default:
        return 'bg-slate-50';
    }
  };

  return (
    <div className={`min-h-screen text-slate-800 flex flex-col font-sans transition-colors duration-300 ${getBackgroundGradient()}`}>
      {/* Sidebar for desktop and drawer for mobile */}
      <Sidebar />

      {/* Main Content Area (offset by 64 / 16rem on desktop) */}
      <div className="flex-1 min-w-0 lg:pl-64 flex flex-col min-h-screen transition-all">
        <Header />

        <main className="flex-1 min-w-0 p-3 sm:p-4 lg:p-7 max-w-[1600px] w-full mx-auto animate-fadeIn">
          {children}
        </main>
      </div>

      {/* Global Interactive Overlays */}
      <SearchModal />
      <NotificationsModal />
    </div>
  );
};
