// Market data types
export interface MarketSummary {
  shIndex: number;
  szIndex: number;
  cybIndex: number;
  shChangePct: number;
  szChangePct: number;
  cybChangePct: number;
  turnover: number;       // 成交额(亿)
  advanceCount: number;   // 上涨家数
  declineCount: number;   // 下跌家数
}

export type MarketStateType = 'bull' | 'bear' | 'neutral';

export interface KlineItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface RealtimeQuote {
  stockCode: string;
  stockName: string;
  currentPrice: number;
  changePct: number;
  volume: number;
  amount: number;   // 成交额
}

export interface SignalItem {
  date: string;
  type: string;
  strength: number;
  description: string;
}

export interface FundFlowItem {
  stockCode: string;
  stockName: string;
  netAmount: number;      // 净流入
  largeOrderPct: number;  // 大单占比
  midOrderPct: number;
  smallOrderPct: number;
  date: string;
}
