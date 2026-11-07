import { CollapsibleSection } from "@/components/collapsible-section"
import { formatDate } from "@/lib/format"

export function Rules({ trainedUntil }: { trainedUntil: string }) {
  return (
    <CollapsibleSection title="Quy tắc khớp lệnh">
      <ul className="list-disc space-y-1 pl-5 text-sm">
        <li>Mô hình AI được huấn luyện đến {formatDate(trainedUntil)}; chỉ dùng tín hiệu của các phiên sau ngày này (trước đó là trong mẫu).</li>
        <li>Lệnh khớp ở giá mở cửa phiên kế tiếp, cộng trượt giá, lô 100 cổ phiếu.</li>
        <li>Mỗi mã mua tối đa 10% khối lượng giao dịch trung bình 20 phiên; không mua mã kịch trần, không bán mã kịch sàn.</li>
        <li>Phí mua 0,15%, phí bán 0,25%. Khoá T+2 tính bằng số phiên giữ tối thiểu.</li>
      </ul>
    </CollapsibleSection>
  )
}
