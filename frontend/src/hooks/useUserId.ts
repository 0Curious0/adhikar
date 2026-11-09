const STORAGE_KEY = 'adhikar.user_id'

// No auth exists anywhere in this backend — /chat, /voice, and /profile/{user_id} just take a
// bare user_id string. Generating and persisting one locally is enough to keep a returning
// visitor's profile (pinned scheme, gathered facts) stable across page loads.
export function useUserId(): string {
  let userId = localStorage.getItem(STORAGE_KEY)
  if (!userId) {
    userId = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, userId)
  }
  return userId
}
