"""RAレコードの構造を解析するデバッグスクリプト.

Usage:
    python debug_ra_record.py
"""
import win32com.client
import pythoncom

def analyze_ra_record():
    """RA レコードの構造を解析."""
    pythoncom.CoInitialize()

    try:
        jv = win32com.client.Dispatch("JVDTLab.JVLink")
        result = jv.JVInit("BAKENKAIGI")
        if result != 0:
            print(f"JVInit failed: {result}")
            return

        # 2026年1月17日のデータを取得
        open_result = jv.JVOpen("RACE", "20260117000000", 1)
        print(f"JVOpen result: {open_result}")

        ra_records = []
        count = 0

        while count < 100:  # 最初の100レコードを取得
            r = jv.JVRead("", 100000, "")
            read_status = r[0]

            if read_status == 0:  # EOF
                break
            if read_status == -1 or read_status == -3:
                continue
            if read_status < 0:
                break

            data = r[1]
            if data[:2] == "RA":
                ra_records.append(data)
                count += 1

                # 11R (カーバンクルステークス) を探す
                race_num = data[25:27]
                if race_num == "11":
                    print(f"\n=== 11R RA Record Analysis ===")
                    print(f"Total length: {len(data)} bytes")
                    print(f"\nFirst 200 bytes (hex):")
                    for i in range(0, min(200, len(data)), 20):
                        hex_str = ' '.join(f'{ord(c):02x}' for c in data[i:i+20])
                        ascii_str = ''.join(c if 32 <= ord(c) < 127 else '.' for c in data[i:i+20])
                        print(f"  [{i:4d}] {hex_str}  |{ascii_str}|")

                    print(f"\nKey positions analysis:")
                    print(f"  [0:2]    RecordType: {repr(data[0:2])}")
                    print(f"  [11:19]  RaceDate:   {repr(data[11:19])}")
                    print(f"  [19:21]  VenueCode:  {repr(data[19:21])}")
                    print(f"  [21:23]  Kai:        {repr(data[21:23])}")
                    print(f"  [23:25]  Nichiji:    {repr(data[23:25])}")
                    print(f"  [25:27]  RaceNum:    {repr(data[25:27])}")

                    # 距離を探す - いくつかの位置を試す
                    print(f"\nSearching for distance (should be 1200 for カーバンクルS):")
                    for pos in [61, 65, 71, 75, 93, 97, 100, 135, 593]:
                        if pos + 4 <= len(data):
                            chunk = data[pos:pos+4]
                            if chunk.strip().isdigit():
                                val = int(chunk.strip())
                                mark = " <-- FOUND!" if val == 1200 else ""
                                print(f"  [{pos:4d}:{pos+4}] = {repr(chunk)} -> {val}{mark}")

                    # 数値っぽいフィールドを探す
                    print(f"\nSearching for 4-digit numeric fields (1000-3600 range):")
                    for pos in range(0, min(800, len(data) - 4)):
                        chunk = data[pos:pos+4]
                        if chunk.strip().isdigit():
                            val = int(chunk.strip())
                            if 1000 <= val <= 3600:
                                print(f"  [{pos:4d}:{pos+4}] = {repr(chunk)} -> {val}m")

        jv.JVClose()

    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    analyze_ra_record()
