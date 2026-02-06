"""pytest configuration for jravan-api tests.

JV-Link (win32com) のモックを設定し、Linux環境でもテストを実行可能にする。
pg8000 のモックを設定し、DB依存なしでテストを実行可能にする。
"""
import sys
from unittest.mock import MagicMock

# win32com と pythoncom のモックを作成
mock_win32com = MagicMock()
mock_pythoncom = MagicMock()

# モジュールキャッシュに追加
sys.modules['win32com'] = mock_win32com
sys.modules['win32com.client'] = mock_win32com.client
sys.modules['pythoncom'] = mock_pythoncom

# pg8000 のモック（DB接続なしでテスト実行するため）
if 'pg8000' not in sys.modules:
    sys.modules['pg8000'] = MagicMock()
