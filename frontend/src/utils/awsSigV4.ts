/**
 * AWS SigV4 署名ユーティリティ
 *
 * Lambda Function URL (AWS_IAM認証) を呼び出すために
 * リクエストに AWS Signature Version 4 署名を付加する。
 */
import { Sha256 } from '@aws-crypto/sha256-js';
import { SignatureV4 } from '@smithy/signature-v4';

const AWS_REGION = import.meta.env.VITE_AWS_REGION || 'ap-northeast-1';
const AWS_ACCESS_KEY_ID = import.meta.env.VITE_STREAMING_ACCESS_KEY_ID || '';
const AWS_SECRET_ACCESS_KEY = import.meta.env.VITE_STREAMING_SECRET_ACCESS_KEY || '';

/**
 * AWS SigV4 署名付きヘッダーを生成する
 *
 * @param url - リクエスト先URL
 * @param body - リクエストボディ（JSON文字列）
 * @returns 署名付きヘッダー
 */
export async function signRequest(url: string, body: string): Promise<HeadersInit> {
  if (!AWS_ACCESS_KEY_ID || !AWS_SECRET_ACCESS_KEY) {
    throw new Error('AWS credentials are not configured');
  }

  const signer = new SignatureV4({
    credentials: {
      accessKeyId: AWS_ACCESS_KEY_ID,
      secretAccessKey: AWS_SECRET_ACCESS_KEY,
    },
    region: AWS_REGION,
    service: 'lambda',
    sha256: Sha256,
  });

  const urlObj = new URL(url);

  const signedRequest = await signer.sign({
    method: 'POST',
    hostname: urlObj.hostname,
    path: urlObj.pathname,
    protocol: urlObj.protocol,
    headers: {
      'Content-Type': 'application/json',
      host: urlObj.hostname,
    },
    body,
  });

  return signedRequest.headers as HeadersInit;
}

/**
 * SigV4 署名が利用可能かどうかをチェック
 */
export function isSigningAvailable(): boolean {
  return !!(AWS_ACCESS_KEY_ID && AWS_SECRET_ACCESS_KEY);
}
