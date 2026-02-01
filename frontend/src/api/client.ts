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
} from '../types';
import { mapApiRaceToRace, mapApiRaceDetailToRaceDetail } from '../types';
import { signRequest, isSigningAvailable } from '../utils/awsSigV4';

// API ベース URL（環境変数から取得）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';
const AGENTCORE_ENDPOINT = import.meta.env.VITE_AGENTCORE_ENDPOINT || '';
const API_KEY = import.meta.env.VITE_API_KEY || '';
// ストリーミングエンドポイント（Lambda Function URL）
const STREAMING_ENDPOINT = import.meta.env.VITE_STREAMING_ENDPOINT || '';

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
  private streamingEndpoint: string;

  constructor(
    baseUrl: string,
    agentCoreEndpoint: string = '',
    apiKey: string = '',
    streamingEndpoint: string = ''
  ) {
    this.baseUrl = baseUrl;
    this.agentCoreEndpoint = agentCoreEndpoint;
    this.apiKey = apiKey;
    this.streamingEndpoint = streamingEndpoint;
  }

  /**
   * 共通ヘッダーを生成する（API Key含む）
   */
  private createHeaders(additionalHeaders: HeadersInit = {}): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(additionalHeaders as Record<string, string>),
    };

    if (this.apiKey) {
      headers['x-api-key'] = this.apiKey;
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
        headers: this.createHeaders(options.headers),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `HTTP ${response.status}`,
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
        headers: this.createHeaders(),
        body: JSON.stringify(request),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `HTTP ${response.status}`,
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

  // AgentCore が利用可能かどうか
  isAgentCoreAvailable(): boolean {
    return !!this.agentCoreEndpoint;
  }

  /**
   * ストリーミングAPIが利用可能かどうか
   * Lambda Function URL + SigV4署名が設定されている場合に true
   */
  isStreamingAvailable(): boolean {
    return !!(this.streamingEndpoint && isSigningAvailable());
  }

  /**
   * ストリーミング対応の AgentCore 相談 API
   *
   * Lambda Function URL (AWS_IAM認証) を使用し、API Gateway の 29秒タイムアウトを回避。
   * 現在の実装では真のストリーミングではなく、長いタイムアウトでの一括レスポンス。
   *
   * @param request - 相談リクエスト
   * @param onComplete - 完了時コールバック
   * @param onError - エラー時コールバック
   */
  async consultWithAgentStreaming(
    request: AgentCoreConsultationRequest,
    onComplete: (response: AgentCoreConsultationResponse) => void,
    onError: (error: string) => void
  ): Promise<void> {
    if (!this.streamingEndpoint) {
      onError('Streaming endpoint is not configured');
      return;
    }

    if (!isSigningAvailable()) {
      onError('AWS credentials are not configured for streaming');
      return;
    }

    const body = JSON.stringify(request);

    try {
      // SigV4署名を取得
      const signedHeaders = await signRequest(this.streamingEndpoint, body);

      const response = await fetch(this.streamingEndpoint, {
        method: 'POST',
        headers: signedHeaders,
        body,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        onError(errorMessage);
        return;
      }

      const data = await response.json();
      onComplete({
        message: data.message || '',
        session_id: data.session_id || '',
      });
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Unknown error');
    }
  }
}

export const apiClient = new ApiClient(
  API_BASE_URL,
  AGENTCORE_ENDPOINT,
  API_KEY,
  STREAMING_ENDPOINT
);
