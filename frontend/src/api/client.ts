import type {
  Race,
  RaceDetail,
  Cart,
  CartItem,
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
  BetOddsResponse,
  BettingRecord,
  BettingSummary,
  BettingRecordFilter,
  LossLimit,
  PendingLossLimitChange,
  LossLimitCheckResult,
  Agent,
  AgentStyleId,
  AgentData,
  AgentReview,
  BettingPreference,
} from '../types';
import { mapApiRaceToRace, mapApiRaceDetailToRaceDetail } from '../types';
import { fetchAuthSession } from 'aws-amplify/auth';
import { getOrCreateGuestId } from '../utils/guestId';

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
  type?: 'consultation' | 'bet_proposal';
  character_type?: 'analyst' | 'intuition' | 'conservative' | 'aggressive';
  agent_data?: AgentData;
  betting_summary?: Record<string, unknown>;
}

export interface BetAction {
  type: 'remove_horse' | 'add_horse' | 'change_amount' | 'replace_bet';
  label: string;
  params: Record<string, unknown>;
}

export interface UsageInfo {
  consulted_races: number;
  max_races: number;
  remaining_races: number;
  tier: 'anonymous' | 'free' | 'premium';
}

export interface AgentCoreConsultationResponse {
  message: string;
  session_id: string;
  suggested_questions?: string[];
  bet_actions?: BetAction[];
  confidence?: number;
  usage?: UsageInfo;
}

export interface RateLimitError {
  error: { message: string; code: string };
  usage: UsageInfo;
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
    let isAuthenticated = false;
    try {
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken?.toString();
      if (idToken) {
        headers['Authorization'] = `Bearer ${idToken}`;
        isAuthenticated = true;
      }
    } catch {
      // 未認証の場合は Authorization ヘッダーなし
    }

    // 未認証時はゲストIDを付与
    if (!isAuthenticated) {
      headers['X-Guest-Id'] = getOrCreateGuestId();
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

  // オッズ取得
  async getBetOdds(
    raceId: string,
    betType: string,
    horseNumbers: number[],
  ): Promise<ApiResponse<BetOddsResponse>> {
    if (!horseNumbers || horseNumbers.length === 0) {
      return { success: false, error: 'Horse numbers must not be empty' };
    }
    const params = new URLSearchParams({
      bet_type: betType,
      horses: horseNumbers.join(','),
    });
    return this.request<BetOddsResponse>(
      `/races/${encodeURIComponent(raceId)}/bet-odds?${params}`
    );
  }

  // カート API
  async getCart(cartId: string): Promise<ApiResponse<Cart>> {
    return this.request<Cart>(`/cart/${cartId}`);
  }

  async addToCart(
    cartId: string,
    item: {
      raceId: string;
      raceName: string;
      betType: BetType;
      horseNumbers: number[];
      amount: number;
    }
  ): Promise<ApiResponse<{ cart_id: string; item_id: string; item_count: number; total_amount: number }>> {
    return this.request<{ cart_id: string; item_id: string; item_count: number; total_amount: number }>('/cart/items', {
      method: 'POST',
      body: JSON.stringify({
        cart_id: cartId || undefined,
        race_id: item.raceId,
        race_name: item.raceName,
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
        // 429: 利用制限超過 — usage 情報を含めて返す
        if (response.status === 429 && data.usage) {
          return {
            success: false,
            error: this.extractErrorMessage(data, response.status),
            data: { usage: data.usage } as unknown as AgentCoreConsultationResponse,
          };
        }
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
    raceNumber: number,
    items?: CartItem[]
  ): Promise<ApiResponse<PurchaseResult>> {
    const payload: Record<string, unknown> = {
      cart_id: cartId,
      race_date: raceDate,
      course_code: courseCode,
      race_number: raceNumber,
    };
    if (items && items.length > 0) {
      payload.items = items.map(item => ({
        race_id: item.raceId,
        race_name: item.raceName,
        bet_type: item.betType,
        horse_numbers: item.horseNumbers,
        amount: item.amount,
        bet_method: item.betMethod || 'normal',
        ...(item.betCount != null ? { bet_count: item.betCount } : {}),
        ...(item.columnSelections ? { column_selections: item.columnSelections } : {}),
      }));
    }
    const res = await this.request<Record<string, unknown>>('/purchases', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.success && res.data) {
      const d = res.data;
      const rawStatus = String(d.status ?? 'pending').toUpperCase();
      const validStatuses = ['PENDING', 'SUBMITTED', 'COMPLETED', 'FAILED'] as const;
      const status = validStatuses.includes(rawStatus as typeof validStatuses[number])
        ? rawStatus as PurchaseResult['status']
        : 'PENDING' as PurchaseResult['status'];
      return { success: true, data: {
        purchaseId: String(d.purchase_id ?? ''),
        status,
        totalAmount: Number(d.total_amount ?? 0),
        createdAt: String(d.created_at ?? ''),
      }};
    }
    return { success: false, error: res.error };
  }

  async getPurchaseHistory(): Promise<ApiResponse<PurchaseOrder[]>> {
    const res = await this.request<Record<string, unknown>[]>('/purchases');
    if (res.success && res.data) {
      return { success: true, data: res.data.map((d) => {
        const rawStatus = String(d.status ?? 'pending').toUpperCase();
        const validStatuses = ['PENDING', 'SUBMITTED', 'COMPLETED', 'FAILED'] as const;
        const status = validStatuses.includes(rawStatus as typeof validStatuses[number])
          ? rawStatus as PurchaseOrder['status']
          : 'PENDING' as PurchaseOrder['status'];
        return {
          purchaseId: String(d.purchase_id ?? ''),
          cartId: String(d.cart_id ?? ''),
          status,
          totalAmount: Number(d.total_amount ?? 0),
          betLineCount: Number(d.bet_line_count ?? 0),
          errorMessage: d.error_message != null ? String(d.error_message) : undefined,
          createdAt: String(d.created_at ?? ''),
          updatedAt: String(d.updated_at || d.created_at || ''),
        };
      })};
    }
    return { success: false, error: res.error };
  }

  async getPurchaseDetail(purchaseId: string): Promise<ApiResponse<PurchaseOrder>> {
    const res = await this.request<Record<string, unknown>>(`/purchases/${encodeURIComponent(purchaseId)}`);
    if (res.success && res.data) {
      const d = res.data;
      const rawStatus = String(d.status ?? 'pending').toUpperCase();
      const validStatuses = ['PENDING', 'SUBMITTED', 'COMPLETED', 'FAILED'] as const;
      const status = validStatuses.includes(rawStatus as typeof validStatuses[number])
        ? rawStatus as PurchaseOrder['status']
        : 'PENDING' as PurchaseOrder['status'];
      return { success: true, data: {
        purchaseId: String(d.purchase_id ?? ''),
        cartId: String(d.cart_id ?? ''),
        status,
        totalAmount: Number(d.total_amount ?? 0),
        betLineCount: Number(d.bet_line_count ?? 0),
        errorMessage: d.error_message != null ? String(d.error_message) : undefined,
        createdAt: String(d.created_at ?? ''),
        updatedAt: String(d.updated_at || d.created_at || ''),
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
      preferredBetTypes?: BetType[];
      axisHorses?: number[];
      characterType?: string;
      maxBets?: number;
      agentData?: AgentData;
    }
  ): Promise<ApiResponse<BetProposalResponse>> {
    const optionParts: string[] = [];
    if (options?.preferredBetTypes?.length) {
      optionParts.push(`希望券種: ${options.preferredBetTypes.join(', ')}`);
    }
    if (options?.axisHorses?.length) {
      optionParts.push(`注目馬: ${options.axisHorses.join(', ')}番`);
    }
    if (!options?.agentData && options?.characterType) {
      optionParts.push(`ペルソナ(character_type): ${options.characterType}`);
    }
    if (options?.maxBets) {
      optionParts.push(`買い目点数上限(max_bets): ${options.maxBets}点`);
    }
    const optionText = optionParts.length > 0 ? ` ${optionParts.join('。')}。` : '';

    const prompt = `レースID ${raceId} について、予算${budget}円で買い目提案を生成してください。${optionText}`;
    const request: AgentCoreConsultationRequest = {
      prompt,
      cart_items: [],
      runners_data: runnersData,
      type: 'bet_proposal',
    };
    if (options?.agentData) {
      request.agent_data = options.agentData;
    }
    const result = await this.consultWithAgent(request);

    if (!result.success || !result.data) {
      return { success: false, error: result.error };
    }

    const message = result.data.message;
    const jsonSeparator = '---BET_PROPOSALS_JSON---';
    const jsonIdx = message.indexOf(jsonSeparator);
    if (jsonIdx === -1) {
      // セパレータがない場合、AIの応答メッセージをエラーとして返す（ツールエラー等のデバッグ用）
      const aiMessage = message.trim();
      return { success: false, error: aiMessage || '提案データが見つかりませんでした' };
    }

    let jsonStr = message.substring(jsonIdx + jsonSeparator.length).trim();
    // コードフェンス除去（```json ... ``` 形式に対応）
    jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/,'');
    // 最初の { から最後の } までを抽出
    const firstBrace = jsonStr.indexOf('{');
    const lastBrace = jsonStr.lastIndexOf('}');
    if (firstBrace === -1 || lastBrace === -1) {
      return { success: false, error: '提案データが見つかりませんでした' };
    }
    jsonStr = jsonStr.substring(firstBrace, lastBrace + 1);
    try {
      const parsed: unknown = JSON.parse(jsonStr);
      if (typeof parsed !== 'object' || parsed === null) {
        return { success: false, error: '提案データの形式が不正です' };
      }
      const data = parsed as { proposed_bets?: unknown; error?: unknown };
      if (!Array.isArray(data.proposed_bets)) {
        const errorMessage =
          typeof data.error === 'string' && data.error.trim().length > 0
            ? data.error
            : '提案データの形式が不正です';
        return { success: false, error: errorMessage };
      }
      // bet_count が欠落している場合のフォールバック（LLMが独自にJSONを生成した場合に起こりうる）
      const bets = data.proposed_bets as Record<string, unknown>[];
      for (const bet of bets) {
        if (bet.bet_count == null) bet.bet_count = 1;
      }
      return { success: true, data: parsed as BetProposalResponse };
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

  // 負け額限度額 API
  async getLossLimit(): Promise<ApiResponse<LossLimit>> {
    const res = await this.request<Record<string, unknown>>('/users/loss-limit');
    if (res.success && res.data) {
      const d = res.data;
      let pendingChange: PendingLossLimitChange | null = null;
      if (d.pending_change && typeof d.pending_change === 'object') {
        const pc = d.pending_change as Record<string, unknown>;
        const rawPcStatus = String(pc.status ?? 'pending').toLowerCase();
        const validPcStatuses = ['pending', 'approved', 'rejected'] as const;
        const pcStatus = validPcStatuses.includes(rawPcStatus as typeof validPcStatuses[number])
          ? rawPcStatus as PendingLossLimitChange['status']
          : 'pending' as PendingLossLimitChange['status'];
        pendingChange = {
          changeId: String(pc.change_id ?? ''),
          changeType: pc.change_type as 'increase' | 'decrease',
          status: pcStatus,
          effectiveAt: String(pc.effective_at ?? ''),
          requestedAt: String(pc.requested_at ?? ''),
          currentLimit: Number(pc.current_limit ?? 0),
          requestedLimit: Number(pc.requested_limit ?? 0),
        };
      }
      return {
        success: true,
        data: {
          lossLimit: (d.loss_limit as number | null) ?? null,
          totalLossThisMonth: (d.total_loss_this_month as number) ?? 0,
          remainingLossLimit: (d.remaining_loss_limit as number | null) ?? null,
          pendingChange,
        },
      };
    }
    return { success: false, error: res.error };
  }

  async setLossLimit(amount: number): Promise<ApiResponse<void>> {
    return this.request<void>('/users/loss-limit', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  }

  async requestLossLimitChange(amount: number): Promise<ApiResponse<PendingLossLimitChange & { appliedImmediately: boolean }>> {
    const res = await this.request<Record<string, unknown>>('/users/loss-limit', {
      method: 'PUT',
      body: JSON.stringify({ amount }),
    });
    if (res.success && res.data) {
      const d = res.data;
      return {
        success: true,
        data: {
          changeId: String(d.change_id ?? ''),
          changeType: d.change_type as 'increase' | 'decrease',
          status: (['pending', 'approved', 'rejected'] as const).includes(
            String(d.status ?? 'pending').toLowerCase() as 'pending' | 'approved' | 'rejected'
          )
            ? String(d.status ?? 'pending').toLowerCase() as PendingLossLimitChange['status']
            : 'pending' as PendingLossLimitChange['status'],
          effectiveAt: String(d.effective_at ?? ''),
          requestedAt: new Date().toISOString(),
          currentLimit: Number(d.current_limit ?? 0),
          requestedLimit: Number(d.requested_limit ?? 0),
          appliedImmediately: Boolean(d.applied_immediately),
        },
      };
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

  async checkLossLimit(amount: number): Promise<ApiResponse<LossLimitCheckResult>> {
    const res = await this.request<Record<string, unknown>>(
      `/users/loss-limit/check?amount=${encodeURIComponent(amount)}`
    );
    if (res.success && res.data) {
      const d = res.data;
      return {
        success: true,
        data: {
          canPurchase: d.can_purchase as boolean,
          remainingAmount: (d.remaining_amount as number | null) ?? null,
          warningLevel: d.warning_level as 'none' | 'caution' | 'warning',
          message: d.message as string,
        },
      };
    }
    return { success: false, error: res.error };
  }

  private mapBettingRecord(d: Record<string, unknown>): BettingRecord {
    const rawStatus = String(d.status ?? 'pending').toUpperCase();
    const validStatuses = ['PENDING', 'SETTLED', 'CANCELLED'] as const;
    const status = validStatuses.includes(rawStatus as typeof validStatuses[number])
      ? rawStatus as BettingRecord['status']
      : 'PENDING' as BettingRecord['status'];
    return {
      recordId: String(d.record_id ?? ''),
      userId: String(d.user_id ?? ''),
      raceId: String(d.race_id ?? ''),
      raceName: String(d.race_name ?? ''),
      raceDate: String(d.race_date ?? ''),
      venue: String(d.venue ?? ''),
      betType: d.bet_type as BettingRecord['betType'],
      horseNumbers: Array.isArray(d.horse_numbers) ? d.horse_numbers as number[] : [],
      amount: Number(d.amount ?? 0),
      payout: Number(d.payout ?? 0),
      profit: Number(d.profit ?? 0),
      status,
      createdAt: String(d.created_at ?? ''),
      settledAt: d.settled_at ? String(d.settled_at) : null,
    };
  }

  // プロフィール更新API
  async updateUserProfile(data: {
    displayName: string;
  }): Promise<ApiResponse<{ user_id: string; email: string; display_name: string }>> {
    return this.request<{ user_id: string; email: string; display_name: string }>('/users/profile', {
      method: 'PUT',
      body: JSON.stringify({
        display_name: data.displayName,
      }),
    });
  }

  // Agent API（エージェント育成）
  async createAgent(name: string, baseStyle: AgentStyleId): Promise<ApiResponse<Agent>> {
    return this.request<Agent>('/agents', {
      method: 'POST',
      body: JSON.stringify({ name, base_style: baseStyle }),
    });
  }

  async getMyAgent(): Promise<ApiResponse<Agent>> {
    return this.request<Agent>('/agents/me');
  }

  async updateAgent(
    baseStyle?: AgentStyleId,
    bettingPreference?: BettingPreference,
    customInstructions?: string | null,
  ): Promise<ApiResponse<Agent>> {
    const payload: Record<string, unknown> = {};
    if (baseStyle !== undefined) {
      payload.base_style = baseStyle;
    }
    if (bettingPreference !== undefined) {
      payload.betting_preference = bettingPreference;
    }
    if (customInstructions !== undefined) {
      payload.custom_instructions = customInstructions;
    }
    return this.request<Agent>('/agents/me', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async getAgentReviews(): Promise<ApiResponse<AgentReview[]>> {
    const res = await this.request<{ reviews: AgentReview[] }>('/agents/me/reviews');
    if (res.success && res.data) {
      return { success: true, data: res.data.reviews };
    }
    return { success: false, error: res.error };
  }

  // AgentCore が利用可能かどうか
  isAgentCoreAvailable(): boolean {
    return !!this.agentCoreEndpoint;
  }
}

export const apiClient = new ApiClient(API_BASE_URL, AGENTCORE_ENDPOINT, API_KEY);
