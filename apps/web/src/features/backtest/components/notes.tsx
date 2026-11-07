import type { Meta } from "@/features/meta/types"

export function Notes({ meta }: { meta: Meta }) {
  return (
    <div className="space-y-6 text-sm">
      <section className="space-y-2">
        <h3 className="text-base font-medium">Các chiến thuật</h3>
        <ul className="list-disc space-y-1 pl-5">
          {meta.strategies.map((strategy) => (
            <li key={strategy.id}>
              <strong className="font-medium">{strategy.label}</strong>: {strategy.help}
            </li>
          ))}
        </ul>
      </section>
      <section className="space-y-2">
        <h3 className="text-base font-medium">Giả định và giới hạn</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Mô hình: dự đoán ngoài mẫu của walk-forward (huấn luyện lại mỗi fold, bỏ 1 phiên giữa train và test), không phải gói <code>models/ensemble3_pooled_1D</code>{" "}
            (đã học cả giai đoạn này nên sẽ rò rỉ).
          </li>
          <li>
            Quy tắc mặc định cho Mô hình AI (mua khi điểm ≥ +0,06, bán khi điểm ≤ −0,10, giữ 3 mã chia đều) được chọn trong 324 cấu hình bằng giai đoạn phát triển (đến hết 2024), rồi kiểm lại ở giai đoạn xác nhận (từ 2025). Vì đã thử nhiều
            cấu hình, kết quả toàn giai đoạn lạc quan hơn thực tế; số đáng tin hơn là giai đoạn xác nhận.
          </li>
          <li>Alpha cổ điển không huấn luyện, nhưng danh sách chiến thuật đã xem trên cùng dữ liệu.</li>
          <li>
            T+2 mô phỏng bằng số phiên giữ tối thiểu. Trượt giá là mức cố định mỗi chiều. Giá trần/sàn chỉ áp ở kiểu khớp mở cửa. Chưa mô hình lô 100 và hàng đợi khớp lệnh.
          </li>
          <li>
            Khoảng tin cậy "đa kiểm định" là Bonferroni cho {meta.strategies.length} chiến thuật có sẵn. Alpha chỉ đáng tin khi khoảng này loại được 0.
          </li>
          <li>19 mã còn niêm yết và có dữ liệu đẹp nên có thiên lệch sống sót. Alpha tính so với trung bình đều 19 mã.</li>
          <li>Danh mục cân bằng đều lại mỗi phiên (bỏ qua trôi trọng số), tiền mặt không sinh lãi.</li>
        </ul>
      </section>
    </div>
  )
}
