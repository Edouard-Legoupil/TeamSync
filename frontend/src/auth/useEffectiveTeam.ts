import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { ALL_TEAMS, useAuth } from './AuthContext'

/**
 * Resolve the team scope for a page from the URL slug (permalink) with a
 * fallback to the global current-team context.
 */
export function useEffectiveTeam(): {
  teamId: string | null
  isAllTeams: boolean
  notFound: boolean
} {
  const { slug } = useParams<{ slug?: string }>()
  const { teams, currentTeamId, setCurrentTeamId, loading } = useAuth()

  const slugTeam = slug ? teams.find((t) => t.slug === slug) : undefined

  // Keep the top-bar switcher in sync when landing on a permalink.
  useEffect(() => {
    if (slugTeam) setCurrentTeamId(slugTeam.id)
  }, [slugTeam?.id, setCurrentTeamId])

  if (slug && !slugTeam && !loading) {
    return { teamId: null, isAllTeams: false, notFound: true }
  }
  if (slugTeam) {
    return { teamId: slugTeam.id, isAllTeams: false, notFound: false }
  }
  return {
    teamId: currentTeamId,
    isAllTeams: currentTeamId === ALL_TEAMS,
    notFound: false,
  }
}
