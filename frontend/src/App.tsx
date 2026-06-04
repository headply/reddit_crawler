import { Fragment, useState } from "react";
import { Dialog, Transition } from "@headlessui/react";
import { Outlet, Route, Routes } from "react-router-dom";
import { X } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { BrowsePage } from "@/pages/BrowsePage";
import { SubredditHealthPage } from "@/pages/SubredditHealthPage";
import { TechTrendsPage } from "@/pages/TechTrendsPage";
import { FilterProvider } from "@/state/filters";

function Layout() {
  const [open, setOpen] = useState(false);
  return (
    <FilterProvider>
      <div className="min-h-screen flex flex-col">
        <TopBar onToggleSidebar={() => setOpen(true)} />
        <div className="flex-1 flex">
          <div className="hidden lg:block">
            <Sidebar />
          </div>
          <main className="flex-1 px-4 sm:px-6 py-5 max-w-[1400px] mx-auto w-full">
            <Outlet />
          </main>
        </div>

        {/* Mobile filters drawer */}
        <Transition show={open} as={Fragment}>
          <Dialog onClose={setOpen} className="relative z-50 lg:hidden">
            <Transition.Child
              as={Fragment}
              enter="transition-opacity duration-150"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="transition-opacity duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <div className="fixed inset-0 bg-black/30" />
            </Transition.Child>
            <Transition.Child
              as={Fragment}
              enter="transition-transform duration-200"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition-transform duration-150"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="fixed inset-y-0 left-0 w-80 max-w-[85%] bg-white shadow-xl overflow-y-auto">
                <div className="flex items-center justify-between px-4 h-14 border-b border-line">
                  <Dialog.Title className="text-sm font-semibold text-ink">
                    Filters
                  </Dialog.Title>
                  <button
                    onClick={() => setOpen(false)}
                    className="w-8 h-8 rounded-md hover:bg-slate-50 inline-flex items-center justify-center text-muted"
                  >
                    <X size={16} />
                  </button>
                </div>
                <Sidebar />
              </Dialog.Panel>
            </Transition.Child>
          </Dialog>
        </Transition>
      </div>
    </FilterProvider>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<BrowsePage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="trends" element={<TechTrendsPage />} />
        <Route path="sources" element={<SubredditHealthPage />} />
      </Route>
    </Routes>
  );
}
