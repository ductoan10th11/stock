import { Trash2 } from "lucide-react"

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"

import { useDeleteAccount } from "../hooks"

export function ManageTab() {
  const remove = useDeleteAccount()
  return (
    <div className="space-y-3">
      <h3 className="text-base font-medium">Xoá tài khoản</h3>
      <p className="text-sm text-muted-foreground">Xoá toàn bộ vị thế, lịch sử lệnh và đường giá trị tài khoản để tạo lại từ đầu. Không hoàn tác được.</p>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="destructive" disabled={remove.isPending}>
            <Trash2 />
            Xoá tài khoản
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá tài khoản giả lập?</AlertDialogTitle>
            <AlertDialogDescription>Toàn bộ vị thế, lịch sử lệnh và đường giá trị sẽ bị xoá và không khôi phục được.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={() => remove.mutate()}>Xoá</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
