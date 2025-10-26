'use client';

import { useState, useMemo } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import ChatInput from '@/components/ChatInput';
import InvestigationPlan from '@/components/InvestigationPlan';
import SearchResults from '@/components/SearchResults';
import VisionResults from '@/components/VisionResults';
import EventLog from '@/components/EventLog';
import ReportModal from '@/components/ReportModal';
import { InvestigationStep, Report, SimilarCase } from '@/types/events';

export default function Home() {
  // Get WebSocket URL from environment
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws';
  const { isConnected, events, sendQuery } = useWebSocket(wsUrl);

  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const openModal = (report: Report) => {
    setSelectedReport(report);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedReport(null);
  };

  // Parse events to extract current state
  const state = useMemo(() => {
    let plan: InvestigationStep[] = [];
    let completedSteps = new Set<number>();
    let searchReports: Report[] = [];
    let searchCount = 0;
    let searchMetadata: any = null;
    let visionCases: SimilarCase[] = [];

    events.forEach((event) => {
      switch (event.type) {
        case 'investigation_plan':
          plan = event.data.plan;
          break;
        case 'step_update':
          if (event.data.status === 'completed') {
            completedSteps.add(event.data.step_number);
          }
          break;
        case 'search_results':
          searchReports = event.data.reports;
          searchCount = event.data.count;
          searchMetadata = event.data.search_metadata;
          break;
        case 'vision_results':
          visionCases = event.data.similar_cases;
          break;
      }
    });

    return {
      plan,
      completedSteps,
      searchReports,
      searchCount,
      searchMetadata,
      visionCases,
    };
  }, [events]);

  return (
    <div className="container">
      <header className="header">
        <h1>Radiology Intelligence Agent</h1>
        <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </header>

      <main className="main">
        {/* Left Panel: Investigation Progress */}
        <aside className="sidebar">
          <InvestigationPlan
            plan={state.plan}
            completedSteps={state.completedSteps}
          />
          <EventLog events={events} />
        </aside>

        {/* Right Panel: Results */}
        <section className="content">
          <div className="results-container">
            <SearchResults
              reports={state.searchReports}
              count={state.searchCount}
              searchMetadata={state.searchMetadata}
              onReportClick={openModal}
            />
            <VisionResults cases={state.visionCases} />
          </div>
        </section>
      </main>

      {/* Bottom: Chat Input */}
      <footer className="footer">
        <ChatInput onSend={sendQuery} isConnected={isConnected} />
      </footer>

      <ReportModal
        isOpen={isModalOpen}
        report={selectedReport}
        onClose={closeModal}
      />
    </div>
  );
}
