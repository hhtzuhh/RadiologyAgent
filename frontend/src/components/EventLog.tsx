'use client';

import { WebSocketEvent } from '@/types/events';

interface EventLogProps {
  events: WebSocketEvent[];
}

export default function EventLog({ events }: EventLogProps) {
  const displayEvents = events.filter(e =>
    e.type === 'agent_message' ||
    e.type === 'connected' ||
    e.type === 'query_received' ||
    e.type === 'tool_call' ||
    e.type === 'completed' ||
    e.type === 'error' ||
    e.type === 'investigation_plan'
  );

  if (displayEvents.length === 0) return null;

  return (
    <div className="event-log">
      <h3>Agent Activity</h3>
      <div className="events">
        {displayEvents.map((event, index) => (
          <div key={index} className={`event event-${event.type}`}>
            {event.type === 'connected' && (
              <span>🟢 {event.data.message}</span>
            )}
            {event.type === 'query_received' && (
              <span>📤 Query: {event.data.query}</span>
            )}
            {event.type === 'tool_call' && (
              <span>🔧 Calling {event.data.tool}: {JSON.stringify(event.data.args)}</span>
            )}
            {event.type === 'agent_message' && (
              <span>💬 {event.data.message}</span>
            )}
            {event.type === 'investigation_plan' && (
              <div>
                <span>📝 Investigation plan created:</span>
                <ul className="list-disc list-inside pl-4 mt-1">
                  {event.data.plan.map((step: any) => (
                    <li key={step.step}>
                      <strong>{step.agent}:</strong> {step.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {event.type === 'completed' && (
              <span>✅ {event.data.message}</span>
            )}
            {event.type === 'error' && (
              <span>❌ Error: {event.data.message}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
