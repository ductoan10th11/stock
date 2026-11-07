import { ApiError } from "@/lib/api-client"

const MESSAGES: Record<string, string> = {
  account_exists: "Đã có tài khoản giả lập. Xoá tài khoản cũ trước khi tạo lại.",
  no_live_data: "Chưa có dữ liệu giá trực tiếp. Bấm Cập nhật dữ liệu trước.",
  model_not_ahead: "Phiên mới nhất chưa sau ngày huấn luyện mô hình. Chờ phiên đóng cửa kế tiếp hoặc chọn chiến thuật không dùng mô hình AI.",
  validation_error: "Thiết lập không hợp lệ.",
}

export function paperErrorMessage(error: Error): string {
  if (!(error instanceof ApiError)) return error.message
  if (error.detail.startsWith("refresh_failed")) return `Cập nhật thất bại: ${error.detail.replace(/^refresh_failed: /, "")}`
  return MESSAGES[error.detail] ?? error.detail
}
