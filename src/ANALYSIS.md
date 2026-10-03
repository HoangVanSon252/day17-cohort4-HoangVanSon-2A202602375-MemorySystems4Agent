# Phân tích kết quả Benchmark

Sau khi triển khai và chạy benchmark cho hai Agent (Baseline và Advanced) trên hai kịch bản (Standard và Long-Context Stress), chúng ta có thể rút ra một số nhận xét và phân tích:

## 1. Tại sao Advanced Agent có Recall tốt hơn Baseline?
Baseline Agent chỉ duy trì bộ nhớ ngắn hạn (within-session) trong cùng một `thread_id`. Do đó, khi các câu hỏi kiểm tra recall được hỏi ở một thread mới hoàn toàn, Baseline Agent mất hoàn toàn context và dẫn đến Recall = 0 (như thấy ở Stress Benchmark) hoặc rất thấp (0.02 ở Standard). 
Trong khi đó, Advanced Agent sử dụng thêm `User.md` (persistent memory) để lưu trữ các thông tin facts quan trọng (tên, nơi ở, nghề nghiệp, sở thích...). Dù sang thread mới, agent vẫn đọc file `User.md` này để nạp lại vào prompt context, giúp nó có thể trả lời các câu hỏi về các thông tin dài hạn với Recall rất cao (0.77 ở Standard và 0.92 ở Stress test).

## 2. Vì sao ở hội thoại ngắn, Advanced Agent có thể tiêu tốn tokens hơn Baseline?
Ở Standard Benchmark (hội thoại ngắn, ít lượt), Baseline Agent chỉ nạp nguyên chuỗi tin nhắn của user và assistant. Trong khi đó, Advanced Agent luôn phải nạp kèm thêm file `User.md` và chuỗi `Summary` (dù ban đầu summary có thể trống) vào mỗi lượt. Sự xuất hiện của các prompt meta-data và context bền vững khiến `Prompt tokens processed` của Advanced Agent (18522 tokens) cao hơn Baseline Agent (12825 tokens) trong các kịch bản hội thoại chưa đủ dài để trigger compaction một cách triệt để, hoặc lượng token overhead bù trừ vào khiến chi phí ban đầu cao hơn.

## 3. Vì sao Compact Memory giúp Advanced Agent có lợi thế ở hội thoại dài?
Ở Long-Context Stress Benchmark, người dùng gửi hàng loạt tin nhắn rất dài (nhiều nội dung dư thừa). Baseline Agent cứ thế cộng dồn toàn bộ raw message vào context. Kết quả là `Prompt tokens processed` của nó phình lên tới 21927 tokens.
Advanced Agent nhờ có `CompactMemoryManager` được cấu hình threshold nhất định, khi chuỗi hội thoại đủ dài, nó sẽ "nén" các tin nhắn cũ thành một chuỗi Summary ngắn gọn (discard các tin nhắn raw cũ) và chỉ giữ nguyên văn vài tin nhắn gần nhất. Điều này đã giúp giảm lượng token đưa vào LLM ở các lượt sau đó rất đáng kể: `Prompt tokens processed` của Advanced giảm xuống chỉ còn 6638 tokens, đồng thời compaction được kích hoạt 11 lần, giúp tiết kiệm chi phí token khổng lồ trong một session dài mà vẫn giữ được logic chính.

## 4. Sự tăng trưởng của Memory File (User.md) và rủi ro đi kèm
Trong quá trình vận hành, `User.md` tăng dần kích thước (hiện đạt 236 bytes ở Standard và 134 bytes ở Stress Test). Sự tăng trưởng này là cần thiết để duy trì fact, tuy nhiên rủi ro dài hạn là:
- **Xung đột thông tin (Conflict):** Người dùng đính chính nơi ở từ Huế sang Đà Nẵng, hệ thống heuristic có thể vô tình gộp hoặc ghi đè sai nếu không đủ thông minh.
- **Phình to kích thước:** Nếu trích xuất mọi chi tiết nhỏ nhặt mà người dùng nói, file này sẽ phình to không kém raw context, làm mất ý nghĩa của "tối ưu context dài hạn".
- **Giải pháp tiềm năng (Bonus):** Áp dụng *Confidence threshold* (chỉ lưu vào profile khi độ tự tin cao hoặc người dùng nhấn mạnh), *Memory decay* (loại bỏ thông tin ít quan trọng theo thời gian), hoặc *Entity Extraction có cấu trúc* để thay thế/xóa các field cũ thay vì chỉ nối dài file text.
