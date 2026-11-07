import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { api, post } from "@/lib/api-client"

import { paperErrorMessage } from "./messages"
import type { CreateAccountRequest, PaperState } from "./types"

export const paperQuery = { queryKey: ["paper"], queryFn: () => api<PaperState>("/paper"), staleTime: 30_000 }

export const usePaperState = () => useQuery(paperQuery)

const refreshDerived = (client: QueryClient) => {
  void client.invalidateQueries({ queryKey: ["paper"] })
  void client.invalidateQueries({ queryKey: ["predictions"] })
}

export function useRefreshPaper() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => post<{ sessions: number }>("/paper/refresh"),
    onSuccess: ({ sessions }) => {
      refreshDerived(client)
      toast.success(sessions ? `Đã xử lý ${sessions} phiên mới.` : "Đã cập nhật dữ liệu. Chưa có phiên mới nào.")
    },
    onError: (error) => toast.error(paperErrorMessage(error)),
  })
}

/** The server answers with the full new state, so show it at once instead of waiting for a refetch. */
export function useCreateAccount() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (request: CreateAccountRequest) => post<PaperState>("/paper", request),
    onSuccess: (state) => {
      client.setQueryData(paperQuery.queryKey, state)
      void client.invalidateQueries({ queryKey: ["predictions"] })
      toast.success("Đã tạo tài khoản giả lập.")
    },
    onError: (error) => toast.error(paperErrorMessage(error)),
  })
}

const withoutAccount = (state: PaperState): PaperState => ({
  ...state, account: null, summary: null, equity: null, orders: [], positions: [], ranking: [], trades: [], score_ready: false, signal_date: null,
})

export function useDeleteAccount() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>("/paper", { method: "DELETE" }),
    onMutate: async () => {
      await client.cancelQueries({ queryKey: paperQuery.queryKey })
      const previous = client.getQueryData<PaperState>(paperQuery.queryKey)
      if (previous) client.setQueryData(paperQuery.queryKey, withoutAccount(previous))
      return { previous }
    },
    onError: (error, _variables, context) => {
      if (context?.previous) client.setQueryData(paperQuery.queryKey, context.previous)
      toast.error(paperErrorMessage(error))
    },
    onSuccess: () => toast.success("Đã xoá tài khoản giả lập."),
    onSettled: () => refreshDerived(client),
  })
}
