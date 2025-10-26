// /*
// /**
//  * ChatInterface Component
//  *
//  * Main chat interface that connects to the WebSocket server,
//  * displays agent thought process and X-ray images in real-time.
//  */

// import React, { useState, useEffect, useRef } from 'react';
// import { XRayImageDisplay } from './XRayImageDisplay';
// import InvestigationPlan from './InvestigationPlan';

// interface Message {
//   role: 'user' | 'agent' | 'system';
//   content: string;
//   timestamp: Date;
//   plan?: Step[];
// }

// interface Step {
//   step_number: number;
//   agent: string;
//   description: string;
//   status: 'pending' | 'in_progress' | 'completed' | 'failed';
//   error?: string;
// }

// export const ChatInterface: React.FC = () => {
//   const [messages, setMessages] = useState<Message[]>([]);
//   const [input, setInput] = useState('');
//   const [isConnected, setIsConnected] = useState(false);
//   const [investigationPlan, setInvestigationPlan] = useState<Step[]>([]);
//   const [currentStep, setCurrentStep] = useState(0);
//   const [searchResults, setSearchResults] = useState<any[]>([]);
//   const [visionResults, setVisionResults] = useState<any[]>([]);
//   const [isLoading, setIsLoading] = useState(false);

//   const wsRef = useRef<WebSocket | null>(null);
//   const messagesEndRef = useRef<HTMLDivElement>(null);

//   // WebSocket connection
//   useEffect(() => {
//     connectWebSocket();
//     return () => {
//       if (wsRef.current) {
//         wsRef.current.close();
//       }
//     };
//   }, []);

//   // Auto-scroll to bottom
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
//   }, [messages]);

//   const connectWebSocket = () => {
//     // Get WebSocket URL from environment variable (Next.js format)
//     const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws';

//     const ws = new WebSocket(wsUrl);

//     ws.onopen = () => {
//       console.log('Connected to agent server');
//       setIsConnected(true);
//       addMessage({ role: 'system', content: 'Connected to Radiology Agent' });
//     };

//     ws.onclose = () => {
//       console.log('Disconnected from agent server');
//       setIsConnected(false);
//       addMessage({ role: 'system', content: 'Disconnected from server' });
//     };

//     ws.onerror = (error) => {
//       console.error('WebSocket error:', error);
//       addMessage({ role: 'system', content: 'Connection error' });
//     };

//     ws.onmessage = (event) => {
//       const data = JSON.parse(event.data);
//       handleServerEvent(data);
//     };

//     wsRef.current = ws;
//   };

//   const handleServerEvent = (event: any) => {
//     const { type, data } = event;

//     switch (type) {
//       case 'connected':
//         console.log('Server confirmed connection');
//         break;

//       case 'agent_thinking':
//         addMessage({ role: 'agent', content: data.message });
//         setIsLoading(true);
//         break;

//       case 'investigation_plan':
//         setInvestigationPlan(data.plan);
//         addMessage({
//           role: 'system',
//           content: `Investigation plan created with ${data.plan.length} steps`,
//           plan: data.plan,
//         });
//         break;

//       case 'tool_call':
//         addMessage({
//           role: 'system',
//           content: `🔧 Calling ${data.tool}: ${data.args.request}`,
//         });
//         break;

//       case 'tool_result':
//         console.log('Tool result:', data);
//         break;

//       case 'search_results':
//         setSearchResults(data.reports);
//         addMessage({ role: 'system', content: `📊 Found ${data.count} relevant reports` });
//         break;

//       case 'vision_results':
//         setVisionResults(data.similar_cases);
//         addMessage({
//           role: 'system',
//           content: `👁️ Found ${data.similar_cases.length} visually similar cases`,
//         });
//         break;

//       case 'step_update':
//         updateInvestigationStep(data.step_number, data.status);
//         if (data.status === 'completed') {
//           setCurrentStep(data.step_number + 1);
//         }
//         break;

//       case 'agent_message':
//         addMessage({ role: 'agent', content: data.message });
//         break;

//       case 'completed':
//         setIsLoading(false);
//         addMessage({ role: 'system', content: '✅ Investigation complete' });
//         break;

//       case 'error':
//         setIsLoading(false);
//         addMessage({ role: 'system', content: `❌ Error: ${data.message}` });
//         break;

//       default:
//         console.log('Unknown event type:', type, data);
//     }
//   };

//   const updateInvestigationStep = (stepNumber: number, status: string) => {
//     setInvestigationPlan((prev) =>
//       prev.map((step) =>
//         step.step_number === stepNumber ? { ...step, status: status as any } : step
//       )
//     );
//   };

//   const addMessage = (message: Omit<Message, 'timestamp'>) => {
//     setMessages((prev) => [
//       ...prev,
//       {
//         ...message,
//         timestamp: new Date(),
//       },
//     ]);
//   };

//   const sendQuery = () => {
//     if (!input.trim() || !isConnected || isLoading) return;

//     // Add user message
//     addMessage({ role: 'user', content: input });

//     // Send to server
//     wsRef.current?.send(JSON.stringify({ query: input }));

//     // Clear input and reset state
//     setInput('');
//     setInvestigationPlan([]);
//     setSearchResults([]);
//     setVisionResults([]);
//     setIsLoading(true);
//   };

//   const handleKeyPress = (e: React.KeyboardEvent) => {
//     if (e.key === 'Enter' && !e.shiftKey) {
//       e.preventDefault();
//       sendQuery();
//     }
//   };

//   return (
//     <div className="h-screen flex flex-col bg-gray-50">
//       {/* Header */}
//       <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
//         <div>
//           <h1 className="text-2xl font-bold text-gray-800">Radiology Intelligence System</h1>
//           <p className="text-sm text-gray-600">Multi-Agent AI for Medical Image Analysis</p>
//         </div>
//         <div className="flex items-center gap-2">
//           <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
//           <span className="text-sm text-gray-600">
//             {isConnected ? 'Connected' : 'Disconnected'}
//           </span>
//         </div>
//       </div>

//       {/* Main Content */}
//       <div className="flex-1 overflow-hidden flex">
//         {/* Left Panel - Chat */}
//         <div className="w-1/2 flex flex-col border-r">
//           {/* Messages */}
//           <div className="flex-1 overflow-y-auto p-6 space-y-4">
//             {messages.map((msg, index) => (
//               <div
//                 key={index}
//                 className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
//               >
//                 <div
//                   className={`
//                     max-w-[80%] rounded-lg px-4 py-3
//                     ${msg.role === 'user' ? 'bg-blue-500 text-white' : ''}
//                     ${msg.role === 'agent' ? 'bg-gray-200 text-gray-800' : ''}
//                     ${msg.role === 'system' ? 'bg-yellow-100 text-yellow-800 text-sm' : ''}
//                   `}
//                 >
//                   <p className="whitespace-pre-wrap">{msg.content}</p>
//                   {msg.plan && <InvestigationPlan plan={msg.plan} />}
//                   <p className="text-xs mt-1 opacity-70">
//                     {msg.timestamp.toLocaleTimeString()}
//                   </p>
//                 </div>
//               </div>
//             ))}
//             <div ref={messagesEndRef} />
//           </div>

//           {/* Input */}
//           <div className="border-t p-4 bg-white">
//             <div className="flex gap-2">
//               <input
//                 type="text"
//                 value={input}
//                 onChange={(e) => setInput(e.target.value)}
//                 onKeyPress={handleKeyPress}
//                 placeholder="Ask about radiology cases..."
//                 className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
//                 disabled={!isConnected || isLoading}
//               />
//               <button
//                 onClick={sendQuery}
//                 disabled={!isConnected || isLoading || !input.trim()}
//                 className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
//               >
//                 {isLoading ? 'Processing...' : 'Send'}
//               </button>
//             </div>
//             <p className="text-xs text-gray-500 mt-2">
//               Example: "Find X-rays similar to patient00002" or "Find cases with pleural effusion"
//             </p>
//           </div>
//         </div>

//         {/* Right Panel - Results */}
//         <div className="w-1/2 flex flex-col overflow-y-auto">
//           <div className="p-6 space-y-6">
//             {/* Search Results */}
//             {searchResults.length > 0 && (
//               <XRayImageDisplay cases={searchResults} title="Search Results" />
//             )}

//             {/* Vision Results */}
//             {visionResults.length > 0 && (
//               <XRayImageDisplay cases={visionResults} title="Visually Similar Cases" />
//             )}

//             {/* Empty State */}
//             {searchResults.length === 0 && visionResults.length === 0 && (
//               <div className="text-center py-12 text-gray-400">
//                 <p className="text-lg">Ask a question to start investigating</p>
//                 <p className="text-sm mt-2">The agent's thought process and results will appear here</p>
//               </div>
//             )}
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };
// */