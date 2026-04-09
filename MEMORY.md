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
