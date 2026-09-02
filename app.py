# === 終極抗噪單數判斷邏輯 ===
    auto_count = 1
    
    # 策略 1：文字正規化（去除全半形括號差異、空格）
    clean_full_text = full_text.replace("（", "(").replace("）", ")").replace(" ", "")
    clean_top_text = top_text.replace("（", "(").replace("）", ")").replace(" ", "")

    # 1-1 正則抽取的數字
    bracket_match = re.search(r'外送\(?(\d+)\)?', clean_full_text) or re.search(r'外送\(?(\d+)\)?', clean_top_text)
    
    if bracket_match:
        auto_count = int(bracket_match.group(1))
    else:
        # 策略 2：如果綠底文字被 OCR 漏掉，直接計算畫面中的「地址數量」
        # Uber Eats 3單會有3個郵遞區號/台灣臺北市/105...
        address_matches = len(re.findall(r'1\d{2}台灣|臺北市|台北市|區|路|街', full_text))
        
        # 策略 3：計算路線節點的個數（計算出現的店家數或送達點）
        # 圖中有 SUKIYA、肯德基、胖老爹 3 家，或 3 個送達地址
        store_and_drop_nodes = len(re.findall(r'105|台灣|店', full_text))
        
        # 精準推算：送達地址行數通常包含台灣或郵遞區號
        tw_address_count = len(re.findall(r'1\d{2}台灣|台灣臺北市', full_text))

        if tw_address_count >= 2:
            auto_count = tw_address_count
        elif address_matches >= 3:
            auto_count = min(3, max(2, address_matches // 2))

    # 強制限制在 1~5 單
    auto_count = max(1, min(auto_count, 5))
