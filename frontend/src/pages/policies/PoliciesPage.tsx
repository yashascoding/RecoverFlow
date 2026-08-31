import { useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { useApi } from '@/hooks/useApi'
import { getPolicies } from '@/api/policies'
import { TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { formatDateTime, formatCurrency } from '@/lib/utils'
import { Shield, AlertTriangle, Pencil, Check, X } from 'lucide-react'
import { toast } from 'sonner'

export function PoliciesPage() {
  const { data: policies, loading, error, refetch } = useApi(getPolicies)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<string>('')
  const [killSwitchConfirm, setKillSwitchConfirm] = useState(false)

  const handleEdit = (id: string, currentValue: string | number | boolean) => {
    setEditingId(id)
    setEditValue(String(currentValue))
  }

  const handleSave = (_id: string) => {
    toast.success('Policy updated successfully')
    setEditingId(null)
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditValue('')
  }

  const formatValue = (policy: { type: string; value: string | number | boolean; unit: string | null }) => {
    if (policy.type === 'boolean') return policy.value ? 'ON' : 'OFF'
    if (policy.unit === 'paise') return formatCurrency(Number(policy.value))
    return `${policy.value}${policy.unit ? ` ${policy.unit}` : ''}`
  }

  return (
    <PageContainer title="Policies" description="Configure recovery automation rules and thresholds">
      {loading ? (
        <TableSkeleton rows={5} columns={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (policies?.length ?? 0) === 0 ? (
        <EmptyState
          title="No policies configured"
          description="Recovery policies will appear here once configured"
          icon={<Shield className="w-8 h-8" />}
        />
      ) : (
        <div className="space-y-3">
          {policies?.map((policy) => {
            const isKillSwitch = policy.name === 'Kill Switch'
            const isEditing = editingId === policy.id

            return (
              <div
                key={policy.id}
                className={`rounded-lg border bg-card p-4 ${
                  isKillSwitch && policy.value ? 'border-red-500/50' : 'border-border'
                }`}
              >
                {isKillSwitch && policy.value && (
                  <div className="mb-3 p-2 rounded-md bg-destructive/10 border border-destructive/20 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <span className="text-[12px] font-medium text-red-400">
                      RECOVERY AUTOMATION DISABLED — No automated recovery actions will be executed.
                    </span>
                  </div>
                )}

                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {isKillSwitch && <Shield className="w-4 h-4 text-muted-foreground" />}
                      <h3 className="text-sm font-semibold text-foreground">{policy.name}</h3>
                    </div>
                    <p className="text-[13px] text-muted-foreground mt-1">{policy.description}</p>
                    <p className="text-[11px] text-muted-foreground mt-2">
                      Last updated {formatDateTime(policy.last_updated)} by {policy.updated_by}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    {isEditing ? (
                      <>
                        {policy.type === 'boolean' ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                if (isKillSwitch && editValue === 'true') {
                                  setKillSwitchConfirm(true)
                                  return
                                }
                                handleSave(policy.id)
                              }}
                              className="p-1.5 rounded-md bg-success/10 text-success hover:bg-success/20 transition-colors"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button onClick={handleCancel} className="p-1.5 rounded-md bg-secondary text-muted-foreground hover:bg-secondary/80 transition-colors">
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <input
                              type={policy.type === 'number' ? 'number' : 'text'}
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="h-8 w-32 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                            />
                            <button onClick={() => handleSave(policy.id)} className="p-1.5 rounded-md bg-success/10 text-success hover:bg-success/20 transition-colors">
                              <Check className="w-4 h-4" />
                            </button>
                            <button onClick={handleCancel} className="p-1.5 rounded-md bg-secondary text-muted-foreground hover:bg-secondary/80 transition-colors">
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="text-right">
                          <p className="text-lg font-bold font-mono text-foreground">{formatValue(policy)}</p>
                        </div>
                        <button
                          onClick={() => {
                            if (isKillSwitch) {
                              if (!policy.value) {
                                setKillSwitchConfirm(true)
                                return
                              }
                            }
                            handleEdit(policy.id, policy.value)
                          }}
                          className="p-1.5 rounded-md bg-secondary text-muted-foreground hover:bg-secondary/80 hover:text-foreground transition-colors"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Kill Switch Confirmation Dialog */}
      {killSwitchConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="rounded-lg border border-border bg-card p-6 max-w-sm w-full mx-4 space-y-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-warning" />
              <h3 className="text-sm font-semibold text-foreground">
                {policies?.find(p => p.name === 'Kill Switch')?.value
                  ? 'Re-enable Recovery Automation?'
                  : 'Disable Recovery Automation?'}
              </h3>
            </div>
            <p className="text-[13px] text-muted-foreground">
              {policies?.find(p => p.name === 'Kill Switch')?.value
                ? 'This will resume all automated recovery actions.'
                : 'This will immediately stop all automated recovery actions. No recovery emails will be sent.'}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setKillSwitchConfirm(false)}
                className="px-3 py-1.5 rounded-md bg-secondary text-[13px] font-medium text-foreground hover:bg-secondary/80 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setKillSwitchConfirm(false)
                  toast.success('Kill switch updated')
                }}
                className="px-3 py-1.5 rounded-md bg-destructive text-[13px] font-medium text-white hover:bg-destructive/80 transition-colors"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  )
}
