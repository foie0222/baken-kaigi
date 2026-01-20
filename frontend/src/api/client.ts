import type {
  Race,
  RaceDetail,
  Cart,
  CartItem,
  ConsultationSession,
  BetType,
  ApiResponse,
} from '../types';

// API ベース URL（環境変数から取得）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
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
  async getRaces(date?: string): Promise<ApiResponse<Race[]>> {
    const params = date ? `?date=${date}` : '';
    return this.request<Race[]>(`/races${params}`);
  }

  async getRaceDetail(raceId: string): Promise<ApiResponse<RaceDetail>> {
    return this.request<RaceDetail>(`/races/${raceId}`);
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
}

export const apiClient = new ApiClient(API_BASE_URL);
