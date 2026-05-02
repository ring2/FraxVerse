// Agent types
export interface AgentOpinion {
  agentId: string;
  agentName: string;
  action: 'buy' | 'sell' | 'hold';
  reason: string;
  confidence: number;
  refuteReason?: string;   // 证伪理由
}

export interface AgentDiscussion {
  id: string;
  stockCode: string;
  stockName: string;
  round: number;
  consensusAction: 'buy' | 'sell' | 'hold';
  consensusScore: number;
  opinions: AgentOpinion[];
  createdAt: string;
}

export interface AgentWeight {
  agentId: string;
  agentName: string;
  weight: number;
  winRate: number;
  totalDecisions: number;
}
