import { useEffect, useState } from 'react'
import { Network } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { TeamRollup, TeamTreeNode } from '../api/types'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'

function TreeNode({ node, depth = 0 }: { node: TeamTreeNode; depth?: number }) {
  return (
    <div style={{ paddingLeft: depth * 20 }}>
      <p className="font-medium text-navy-900">{node.name}</p>
      {node.description && <p className="text-xs text-muted">{node.description}</p>}
      {node.children.map((child) => (
        <TreeNode key={child.id} node={child} depth={depth + 1} />
      ))}
    </div>
  )
}

export default function TeamsPage() {
  const { currentTeamId } = useAuth()
  const [tree, setTree] = useState<TeamTreeNode | null>(null)
  const [rollup, setRollup] = useState<TeamRollup | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!currentTeamId) return
    setLoading(true)
    Promise.all([
      api.get<TeamTreeNode>(`/teams/${currentTeamId}/tree`),
      api.get<TeamRollup>(`/teams/${currentTeamId}/rollup`),
    ])
      .then(([t, r]) => {
        setTree(t.data)
        setRollup(r.data)
      })
      .finally(() => setLoading(false))
  }, [currentTeamId])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold text-navy-900">Team Structure</h1>
      <p className="text-sm text-muted">
        Organigramme and roll-up across child teams.
      </p>

      {rollup && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card className="p-4">
            <p className="text-2xl font-semibold text-navy-900">
              {rollup.descendant_count}
            </p>
            <p className="text-sm text-muted">Teams in hierarchy</p>
          </Card>
          <Card className="p-4">
            <p className="text-2xl font-semibold text-navy-900">
              {rollup.open_action_items}
            </p>
            <p className="text-sm text-muted">Open action items</p>
          </Card>
          <Card className="p-4">
            <p className="text-2xl font-semibold text-navy-900">
              {rollup.recent_meetings.length}
            </p>
            <p className="text-sm text-muted">Recent meetings (5 max)</p>
          </Card>
        </div>
      )}

      <Card className="mt-6">
        <h2 className="mb-4 text-base font-semibold text-navy-900">Hierarchy</h2>
        {tree ? (
          <TreeNode node={tree} />
        ) : (
          <EmptyState
            icon={<Network className="h-8 w-8" />}
            title="No hierarchy"
            description="This team has no child teams."
          />
        )}
      </Card>
    </div>
  )
}
