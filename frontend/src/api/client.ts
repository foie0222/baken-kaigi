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

// API ベース URL（環境変数から取得）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';
const AGENTCORE_ENDPOINT = import.meta.env.VITE_AGENTCORE_ENDPOINT || '';

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
}

class ApiClient {
  private baseUrl: string;
  private agentCoreEndpoint: string;

  constructor(baseUrl: string, agentCoreEndpoint: string = '') {
    this.baseUrl = baseUrl;
    this.agentCoreEndpoint = agentCoreEndpoint;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
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
        headers: {
          'Content-Type': 'application/json',
        },
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
}

export const apiClient = new ApiClient(API_BASE_URL, AGENTCORE_ENDPOINT);
