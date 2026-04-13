# MEMORY.md

## Koxuan 偏好與持續設定

- 偏好以繁體中文溝通。
- 涉及安裝、修改設定、重啟服務、開 tunnel、對外操作或其他會造成狀態變更的動作，需先取得 Koxuan 明確同意。
- 已建立並使用 LINE 作為與助手溝通的管道之一。
- Koxuan 希望重要需求不要只留在對話中，要落到記憶檔、排程與狀態檔。
- Koxuan 希望我主動注意對話 token / context 使用量；若接近上限，應主動提醒並協助切換到新對話，避免上下文過滿。
- 對話 context 使用量達到約 80% 時，應主動提醒 Koxuan 準備切換到新對話。

## 已建立的提醒 / 監控

- US market 15m monitor：美股監控提醒，透過 cron 定期執行並送到 LINE。
- Trump Truth important alerts：川普 Truth Social 重大發言提醒，透過 cron 定期執行並送到 LINE。
- Trump Truth daily digest：川普 Truth Social 每日摘要，透過 cron 定期執行並送到 LINE。
- Canon RF45 stock watch：Canon RF45 庫存監控，透過 cron 定期執行並送到 LINE。

## 備註

- 上述提醒除了記憶外，也依賴 OpenClaw cron jobs 與 memory/*.json 狀態檔持續運作。
- 若提醒失效，優先檢查 cron job 是否被停用、LINE webhook / tunnel 是否失效、以及模型使用額度是否觸發 rate limit。

## 近期重要對話脈絡

- 2026-04-09 主要在處理 doggo-dashboard 與 LINE 溝通橋樑。Dashboard 方向明確偏好可愛、像素風、像星之卡比戰鬥框的狗狗 HUD，主角是狗狗，並持續強化互動感與公開展示效果。
- Dashboard 公開版後續重點包含：川普發言區塊要有英文原文加繁中翻譯、留言板要做成可公開展示的 8-bit 風格；翻譯文案偏好自然、台灣常用語感，不要生硬直譯。
- 2026-04-10 有一段長對話在排查 LINE 橋樑與 cron 傳送異常，脈絡包含：檢查 gateway / cron / 狀態檔、發現 webhook 404、重新確認 ngrok / LINE webhook 狀態，以及追蹤 daily digest 的 rate limit 問題。
- 2026-04-13 討論 5/15-5/19 韓國生日行、5/21-5/30 日本行與中間只回台一天的安排。核心結論是：技術上可行，但若日本已是固定主線，韓國屬於為女友生日加上的行程，需在「值得衝的情緒價值」與「上班一天後又出發的疲勞」之間取捨；國內生日小旅行是更穩的替代方案。
- Koxuan 不希望每次開新對話都要重新交代上述脈絡，若後續再談 dashboard、LINE 橋樑、cron、韓國生日行或日本行，應主動接續這些背景。
