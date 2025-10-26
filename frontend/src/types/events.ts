// Event types from WebSocket server

export interface InvestigationStep {
  step: number;
  agent: string;
  description: string;
}

export interface Report {
  patient_id: string;
  report_text: string;
  score: number;
  chexbert_labels?: any;
  image_url?: string;
}

export interface SimilarCase {
  patient_id: string;
  report_text: string;
  similarity_score: number;
  image_url?: string;
}

export type WebSocketEvent =
  | { type: 'connected'; data: { message: string; user_id: string } }
  | { type: 'query_received'; data: { query: string } }
  | { type: 'investigation_plan'; data: { plan: InvestigationStep[] } }
  | { type: 'tool_call'; data: { tool: string; args: any } }
  | { type: 'search_results'; data: { reports: Report[]; count: number; search_metadata: any } }
  | { type: 'vision_results'; data: { similar_cases: SimilarCase[]; metadata: any } }
  | { type: 'step_update'; data: { step_number: number; status: string } }
  | { type: 'agent_message'; data: { message: string } }
  | { type: 'completed'; data: { message: string } }
  | { type: 'error'; data: { message: string } };
