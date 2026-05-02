// Position types
export interface PositionItem {
  id: string;
  stockCode: string;
  stockName: string;
  volume: number;
  avgCost: number;
  currentPrice: number;
  marketValue: number;
  pnl: number;
  pnlPct: number;
  strategy: string;
  openedAt: string;
}

export interface TradeOrder {
  id: string;
  stockCode: string;
  stockName: string;
  direction: 'buy' | 'sell';
  orderType: 'market' | 'limit';
  price: number;
  volume: number;
  filledVolume: number;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface SubmitOrderRequest {
  stockCode: string;
  direction: 'buy' | 'sell';
  orderType: 'market' | 'limit';
  price?: number;
  volume: number;
  stopLossPrice?: number;
  stopProfitPrice?: number;
}

export interface SubmitOrderResult {
  orderId: string;
  status: string;
}

export interface StopLossCondition {
  id: string;
  stockCode: string;
  stockName: string;
  type: 'fixed' | 'trailing' | 'percent' | 'amount';
  triggerPrice: number;
  currentPrice: number;
  status: 'active' | 'triggered' | 'cancelled';
  createdAt: string;
}

export type TradeMode = 'SIMULATION' | 'PAPER' | 'LIVE';
