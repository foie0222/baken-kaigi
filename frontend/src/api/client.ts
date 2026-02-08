import type {
  Race,
  RaceDetail,
  Cart,
  CartItem,
  ConsultationSession,
  BetType,
  ApiResponse,
  ApiRacesResponse,
  ApiRaceDetailResponse,
  RunnerData,
  PurchaseResult,
  PurchaseOrder,
  IpatCredentialsInput,
  IpatStatus,
  IpatBalance,
  BetProposalResponse,
  BettingRecord,
  BettingSummary,
  BettingRecordFilter,
} from '../types';
import { mapApiRaceToRace, mapApiRaceDetailToRaceDetail } from '../types';
import { fetchAuthSession } from 'aws-amplify/auth';

// API ベース URL（環境変数から取得）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';
const AGENTCORE_ENDPOINT = import.meta.env.VITE_AGENTCORE_ENDPOINT || '';
const API_KEY = import.meta.env.VITE_API_KEY || '';

// AgentCore 相談リクエスト/レスポンス型
export interface AgentCoreConsultationRequest {
  prompt: string;
  cart_items: Array<{
    raceId: string;
    raceName: string;
    betType: string;
    horseNumbers: number[];
    amount: number;
  }>;
  runners_data?: RunnerData[];
  session_id?: string;
}

export interface AgentCoreConsultationResponse {
  message: string;
  session_id: string;
  suggested_questions?: string[];
  confidence?: number;
}

class ApiClient {
  private baseUrl: string;
  private agentCoreEndpoint: string;
  private apiKey: string;

  constructor(baseUrl: string, agentCoreEndpoint: string = '', apiKey: string = '') {
    this.baseUrl = baseUrl;
    this.agentCoreEndpoint = agentCoreEndpoint;
    this.apiKey = apiKey;
  }

  /**
   * APIエラーレスポンスからエラーメッセージ文字列を抽出する
   * バックエンドは {error: {message, code}} または {error: "string"} の形式で返す
   */
  private extractErrorMessage(data: Record<string, unknown>, statusCode: number): string {
    const err = data.error;
    if (err && typeof err === 'object' && 'message' in (err as Record<string, unknown>)) {
      return (err as Record<string, string>).message;
    }
    if (typeof err === 'string') {
      return err;
    }
    return `HTTP ${statusCode}`;
  }

  /**
   * 共通ヘッダーを生成する（API Key含む）
   */
  private async createHeaders(additionalHeaders: HeadersInit = {}): Promise<HeadersInit> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(additionalHeaders as Record<string, string>),
    };

    if (this.apiKey) {
      headers['x-api-key'] = this.apiKey;
    }

    // Cognito認証トークンを付与（ログイン済みの場合）
    try {
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken?.toString();
      if (idToken) {
        headers['Authorization'] = `Bearer ${idToken}`;
      }
    } catch {
      // 未認証の場合は Authorization ヘッダーなし
    }

    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: await this.createHeaders(options.headers),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: this.extractErrorMessage(data, response.status),
        };
      }

      return {
        success: true,
        data: data.data || data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // レース API
  async getRaces(date?: string): Promise<ApiResponse<{ races: Race[]; venues: string[] }>> {
    const params = date ? `?date=${date}` : '';
    const response = await this.request<ApiRacesResponse>(`/races${params}`);

    if (!response.success || !response.data) {
      return { success: false, error: response.error };
    }

    return {
      success: true,
      data: {
        races: response.data.races.map(mapApiRaceToRace),
        venues: response.data.venues,
      },
    };
  }

  async getRaceDetail(raceId: string): Promise<ApiResponse<RaceDetail>> {
    const response = await this.request<ApiRaceDetailResponse>(
      `/races/${encodeURIComponent(raceId)}`
    );

    if (!response.success || !response.data) {
      return { success: false, error: response.error };
    }

    return {
      success: true,
      data: mapApiRaceDetailToRaceDetail(response.data.race, response.data.runners),
    };
  }

  async getRaceDates(from?: string, to?: string): Promise<ApiResponse<string[]>> {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    const queryString = params.toString();
    const response = await this.request<{ dates: string[] }>(
      `/race-dates${queryString ? `?${queryString}` : ''}`
    );

    if (!response.success || !response.data) {
      return { success: false, error: response.error };
    }

    return {
      success: true,
      data: response.data.dates,
    };
  }

  // カート API
  async getCart(cartId: string): Promise<ApiResponse<Cart>> {
    return this.request<Cart>(`/cart/${cartId}`);
  }

  async addToCart(
    cartId: string,
    item: {
      raceId: string;
      betType: BetType;
      horseNumbers: number[];
      amount: number;
    }
  ): Promise<ApiResponse<CartItem>> {
    return this.request<CartItem>('/cart/items', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId,
        race_id: item.raceId,
        bet_type: item.betType,
        horse_numbers: item.horseNumbers,
        amount: item.amount,
      }),
    });
  }

  async removeFromCart(
    cartId: string,
    itemId: string
  ): Promise<ApiResponse<void>> {
    return this.request<void>(`/cart/${cartId}/items/${itemId}`, {
      method: 'DELETE',
    });
  }

  async clearCart(cartId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/cart/${cartId}`, {
      method: 'DELETE',
    });
  }

  // 相談 API
  async startConsultation(
    cartId: string
  ): Promise<ApiResponse<ConsultationSession>> {
    return this.request<ConsultationSession>('/consultations', {
      method: 'POST',
      body: JSON.stringify({ cart_id: cartId }),
    });
  }

  async sendMessage(
    sessionId: string,
    content: string
  ): Promise<ApiResponse<ConsultationSession>> {
    return this.request<ConsultationSession>(
      `/consultations/${sessionId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({ content }),
      }
    );
  }

  async getConsultation(
    sessionId: string
  ): Promise<ApiResponse<ConsultationSession>> {
    return this.request<ConsultationSession>(`/consultations/${sessionId}`);
  }

  // AgentCore 相談 API
  async consultWithAgent(
    request: AgentCoreConsultationRequest
  ): Promise<ApiResponse<AgentCoreConsultationResponse>> {
    if (!this.agentCoreEndpoint) {
      return {
        success: false,
        error: 'AgentCore endpoint is not configured',
      };
    }

    try {
      const response = await fetch(this.agentCoreEndpoint, {
        method: 'POST',
        headers: await this.createHeaders(),
        body: JSON.stringify(request),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: this.extractErrorMessage(data, response.status),
        };
      }

      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // 購入API
  async submitPurchase(
    cartId: string,
    raceDate: string,
    courseCode: string,
    raceNumber: number
  ): Promise<ApiResponse<PurchaseResult>> {
    const res = await this.request<Record<string, unknown>>('/purchases', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId,
        race_date: raceDate,
        course_code: courseCode,
        race_number: raceNumber,
      }),
    });
    if (res.success && res.data) {
      const d = res.data;
      return { success: true, data: {
        purchaseId: d.purchase_id as string,
        status: (d.status as string).toUpperCase() as PurchaseResult['status'],
        totalAmount: d.total_amount as number,
        createdAt: d.created_at as string,
      }};
    }
    return { success: false, error: res.error };
  }

  async getPurchaseHistory(): Promise<ApiResponse<PurchaseOrder[]>> {
    const res = await this.request<Record<string, unknown>[]>('/purchases');
    if (res.success && res.data) {
      return { success: true, data: res.data.map((d) => ({
        purchaseId: d.purchase_id as string,
        cartId: (d.cart_id as string) || '',
        status: (d.status as string).toUpperCase() as PurchaseOrder['status'],
        totalAmount: d.total_amount as number,
        betLineCount: (d.bet_line_count as number) || 0,
        errorMessage: d.error_message as string | undefined,
        createdAt: d.created_at as string,
        updatedAt: (d.updated_at as string) || (d.created_at as string),
      }))};
    }
    return { success: false, error: res.error };
  }

  async getPurchaseDetail(purchaseId: string): Promise<ApiResponse<PurchaseOrder>> {
    const res = await this.request<Record<string, unknown>>(`/purchases/${encodeURIComponent(purchaseId)}`);
    if (res.success && res.data) {
      const d = res.data;
      return { success: true, data: {
        purchaseId: d.purchase_id as string,
        cartId: (d.cart_id as string) || '',
        status: (d.status as string).toUpperCase() as PurchaseOrder['status'],
        totalAmount: d.total_amount as number,
        betLineCount: (d.bet_line_count as number) || 0,
        errorMessage: d.error_message as string | undefined,
        createdAt: d.created_at as string,
        updatedAt: (d.updated_at as string) || (d.created_at as string),
      }};
    }
    return { success: false, error: res.error };
  }

  // IPAT設定API
  async saveIpatCredentials(credentials: IpatCredentialsInput): Promise<ApiResponse<void>> {
    return this.request<void>('/settings/ipat', {
      method: 'PUT',
      body: JSON.stringify({
        inet_id: credentials.inetId,
        subscriber_number: credentials.subscriberNumber,
        pin: credentials.pin,
        pars_number: credentials.parsNumber,
      }),
    });
  }

  async getIpatStatus(): Promise<ApiResponse<IpatStatus>> {
    return this.request<IpatStatus>('/settings/ipat');
  }

  async deleteIpatCredentials(): Promise<ApiResponse<void>> {
    return this.request<void>('/settings/ipat', {
      method: 'DELETE',
    });
  }

  // 残高照会
  async getIpatBalance(): Promise<ApiResponse<IpatBalance>> {
    const res = await this.request<Record<string, unknown>>('/ipat/balance');
    if (res.success && res.data) {
      const d = res.data;
      return { success: true, data: {
        betDedicatedBalance: d.bet_dedicated_balance as number,
        settlePossibleBalance: d.settle_possible_balance as number,
        betBalance: d.bet_balance as number,
        limitVoteAmount: d.limit_vote_amount as number,
      }};
    }
    return { success: false, error: res.error };
  }

  // AI買い目提案
  async requestBetProposal(
    raceId: string,
    budget: number,
    runnersData: RunnerData[],
    options?: {
      preferredBetTypes?: string[];
      axisHorses?: number[];
    }
  ): Promise<ApiResponse<BetProposalResponse>> {
    const optionParts: string[] = [];
    if (options?.preferredBetTypes?.length) {
      optionParts.push(`希望券種: ${options.preferredBetTypes.join(', ')}`);
    }
    if (options?.axisHorses?.length) {
      optionParts.push(`注目馬: ${options.axisHorses.join(', ')}番`);
    }
    const optionText = optionParts.length > 0 ? ` ${optionParts.join('。')}。` : '';

    const prompt = `レースID ${raceId} について、予算${budget}円でgenerate_bet_proposalツールを使って買い目提案を生成してください。${optionText}`;
    const result = await this.consultWithAgent({
      prompt,
      cart_items: [],
      runners_data: runnersData,
    });

    if (!result.success || !result.data) {
      return { success: false, error: result.error };
    }

    const message = result.data.message;
    const jsonSeparator = '---BET_PROPOSALS_JSON---';
    const jsonIdx = message.indexOf(jsonSeparator);
    if (jsonIdx === -1) {
      return { success: false, error: '提案データが見つかりませんでした' };
    }

    const jsonStr = message.substring(jsonIdx + jsonSeparator.length).trim();
    try {
      const data = JSON.parse(jsonStr) as BetProposalResponse;
      return { success: true, data };
    } catch {
      return { success: false, error: '提案データの解析に失敗しました' };
    }
  }

  // 賭け記録API
  async createBettingRecord(data: {
    raceId: string;
    raceName: string;
    raceDate: string;
    venue: string;
    betType: string;
    horseNumbers: number[];
    amount: number;
  }): Promise<ApiResponse<BettingRecord>> {
    const res = await this.request<Record<string, unknown>>('/betting-records', {
      method: 'POST',
      body: JSON.stringify({
        race_id: data.raceId,
        race_name: data.raceName,
        race_date: data.raceDate,
        venue: data.venue,
        bet_type: data.betType,
        horse_numbers: data.horseNumbers,
        amount: data.amount,
      }),
    });
    if (res.success && res.data) {
      return { success: true, data: this.mapBettingRecord(res.data) };
    }
    return { success: false, error: res.error };
  }

  async getBettingRecords(filters?: BettingRecordFilter): Promise<ApiResponse<BettingRecord[]>> {
    const params = new URLSearchParams();
    if (filters?.dateFrom) params.set('date_from', filters.dateFrom);
    if (filters?.dateTo) params.set('date_to', filters.dateTo);
    if (filters?.venue) params.set('venue', filters.venue);
    if (filters?.betType) params.set('bet_type', filters.betType);
    const queryString = params.toString();
    const res = await this.request<Record<string, unknown>[]>(
      `/betting-records${queryString ? `?${queryString}` : ''}`
    );
    if (res.success && res.data) {
      return { success: true, data: res.data.map((d) => this.mapBettingRecord(d)) };
    }
    return { success: false, error: res.error };
  }

  async getBettingSummary(period: 'this_month' | 'last_month' | 'all_time'): Promise<ApiResponse<BettingSummary>> {
    const res = await this.request<Record<string, unknown>>(
      `/betting-records/summary?period=${period}`
    );
    if (res.success && res.data) {
      const d = res.data;
      return { success: true, data: {
        totalInvestment: d.total_investment as number,
        totalPayout: d.total_payout as number,
        netProfit: d.net_profit as number,
        winRate: d.win_rate as number,
        recordCount: d.record_count as number,
        roi: d.roi as number,
      }};
    }
    return { success: false, error: res.error };
  }

  private mapBettingRecord(d: Record<string, unknown>): BettingRecord {
    return {
      recordId: d.record_id as string,
      userId: d.user_id as string,
      raceId: d.race_id as string,
      raceName: d.race_name as string,
      raceDate: d.race_date as string,
      venue: d.venue as string,
      betType: d.bet_type as BettingRecord['betType'],
      horseNumbers: d.horse_numbers as number[],
      amount: d.amount as number,
      payout: d.payout as number,
      profit: d.profit as number,
      status: (d.status as string).toUpperCase() as BettingRecord['status'],
      createdAt: d.created_at as string,
      settledAt: (d.settled_at as string | null) || null,
    };
  }

  // AgentCore が利用可能かどうか
  isAgentCoreAvailable(): boolean {
    return !!this.agentCoreEndpoint;
  }
}

export const apiClient = new ApiClient(API_BASE_URL, AGENTCORE_ENDPOINT, API_KEY);
